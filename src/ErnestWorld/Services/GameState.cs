using System.Text.Json;
using System.Text.Json.Serialization;
using ErnestWorld.Data;
using ErnestWorld.Game;

namespace ErnestWorld.Services;

/// <summary>Ce qui est sauvegardé dans le navigateur du visiteur.</summary>
public sealed record SaveData(
    List<string> Visited,
    List<string> Read,
    List<string> Achievements,
    List<string> Flags,
    string? Name,
    List<string>? Bosses = null);

[JsonSerializable(typeof(SaveData))]
internal partial class SaveJsonContext : JsonSerializerContext;

/// <summary>
/// La progression du visiteur : lieux découverts, articles lus, boss vaincus, succès, XP et rang.
/// Tout reste dans son navigateur (localStorage) : rien n'est envoyé sur un serveur.
/// </summary>
public sealed class GameState(BrowserService browser, ToastService toasts)
{
    private const string StorageKey = "ernest-world-v1";

    private readonly HashSet<string> _visited = [];
    private readonly HashSet<string> _read = [];
    private readonly HashSet<string> _achievements = [];
    private readonly HashSet<string> _flags = [];
    private readonly HashSet<string> _bosses = [];
    private HashSet<string> _knownPosts = [];
    private Task? _loading;

    /// <summary>Déclenché après chaque changement, pour rafraîchir l'interface.</summary>
    public event Action? Changed;

    public IReadOnlySet<string> Visited => _visited;
    public string? VisitorName { get; private set; }

    public bool HasVisited(string placeId) => _visited.Contains(placeId);
    public bool HasRead(string slug) => _read.Contains(slug);
    public bool HasFlag(string flag) => _flags.Contains(flag);
    public bool IsUnlocked(string achievementId) => _achievements.Contains(achievementId);
    public bool HasDefeated(string bossId) => _bosses.Contains(bossId);

    public int AchievementCount => _achievements.Count;
    public int ReadCount => _read.Count;
    public int DefeatedCount => _bosses.Count;
    public int DiscoveredRegular => Island.Regular.Count(p => _visited.Contains(p.Id));
    public bool AllRegularDiscovered => Island.Regular.All(p => _visited.Contains(p.Id));

    public int Xp =>
        _visited.Count * Rules.XpPerPlace
        + _read.Count * Rules.XpPerPost
        + _achievements.Count * Rules.XpPerAchievement
        + (_flags.Contains(Flags.Subscribed) ? Rules.XpSubscribe : 0)
        + (_flags.Contains(Flags.Tour) ? Rules.XpTour : 0)
        + Bestiary.All.Where(b => _bosses.Contains(b.Id)).Sum(b => b.XpReward);

    public Level Level => Rules.LevelFor(Xp);

    /// <summary>Charge la sauvegarde une seule fois, même si plusieurs composants le demandent.</summary>
    public Task LoadAsync() => _loading ??= LoadCoreAsync();

    private async Task LoadCoreAsync()
    {
        var json = await browser.GetAsync(StorageKey);
        if (string.IsNullOrEmpty(json))
        {
            return;
        }

        try
        {
            var data = JsonSerializer.Deserialize(json, SaveJsonContext.Default.SaveData);
            if (data is null)
            {
                return;
            }

            _visited.UnionWith(data.Visited.Where(id => Island.Find(id) is not null));
            _read.UnionWith(data.Read);
            _achievements.UnionWith(data.Achievements.Where(id => Rules.Achievements.Any(a => a.Id == id)));
            _flags.UnionWith(data.Flags);
            _bosses.UnionWith((data.Bosses ?? []).Where(id => Bestiary.Find(id) is not null));
            VisitorName = data.Name;
            Changed?.Invoke();
        }
        catch (JsonException)
        {
            // Sauvegarde abîmée : on repart de zéro plutôt que de bloquer le site.
        }
    }

    /// <summary>Marque un lieu comme découvert. Renvoie vrai s'il était nouveau.</summary>
    public Task<bool> VisitAsync(string placeId) => ApplyAsync(() => _visited.Add(placeId));

    /// <summary>Marque un article comme lu. Renvoie vrai s'il était nouveau.</summary>
    public Task<bool> MarkReadAsync(string slug) => ApplyAsync(() => _read.Add(slug));

    /// <summary>Enregistre une action spéciale (abonnement, mode nuit…). Renvoie vrai si c'est la première fois.</summary>
    public Task<bool> SetFlagAsync(string flag) => ApplyAsync(() => _flags.Add(flag));

    /// <summary>Enregistre une victoire contre un boss. Renvoie vrai si c'est la première victoire contre lui.</summary>
    public async Task<bool> DefeatBossAsync(string bossId, bool flawless)
    {
        var first = false;
        await ApplyAsync(() =>
        {
            first = _bosses.Add(bossId);
            var flawlessAdded = flawless && _flags.Add(Flags.Flawless);
            return first || flawlessAdded;
        });
        return first;
    }

    public Task<bool> SetNameAsync(string? name)
    {
        var clean = string.IsNullOrWhiteSpace(name) ? null : name.Trim()[..Math.Min(name.Trim().Length, 24)];
        return ApplyAsync(() =>
        {
            var changed = clean != VisitorName;
            VisitorName = clean;
            return changed;
        });
    }

    /// <summary>Le Journal indique quels articles existent, pour le succès « Érudit ».</summary>
    public Task SetKnownPostsAsync(IEnumerable<string> slugs) =>
        ApplyAsync(() =>
        {
            var next = slugs.ToHashSet();
            var changed = !next.SetEquals(_knownPosts);
            _knownPosts = next;
            return changed;
        });

    /// <summary>Efface toute la progression.</summary>
    public async Task ResetAsync()
    {
        _visited.Clear();
        _read.Clear();
        _achievements.Clear();
        _flags.Clear();
        _bosses.Clear();
        VisitorName = null;
        await SaveAsync();
        Changed?.Invoke();
    }

    private async Task<bool> ApplyAsync(Func<bool> mutation)
    {
        await LoadAsync();
        var rankBefore = Level.Number;
        if (!mutation())
        {
            return false;
        }

        UnlockAchievements();

        var rank = Level;
        if (rank.Number > rankBefore)
        {
            toasts.Show("Nouveau rang", $"Rang {rank.Number} · {rank.Title}", "crown");
        }

        await SaveAsync();
        Changed?.Invoke();
        return true;
    }

    private void UnlockAchievements()
    {
        foreach (var id in EarnedAchievements())
        {
            if (_achievements.Add(id))
            {
                var achievement = Rules.Achievements.First(a => a.Id == id);
                toasts.Show("Succès débloqué", $"{achievement.Name} · +{Rules.XpPerAchievement} XP", achievement.Icon);
            }
        }
    }

    private IEnumerable<string> EarnedAchievements()
    {
        if (_visited.Count >= 1) yield return "premier-pas";
        if (Island.Places.All(p => _visited.Contains(p.Id))) yield return "cartographe";
        if (_read.Count >= 1) yield return "lecteur";
        if (_knownPosts.Count > 0 && _knownPosts.IsSubsetOf(_read)) yield return "erudit";
        if (_flags.Contains(Flags.Subscribed)) yield return "messager";
        if (_flags.Contains(Flags.Night)) yield return "oiseau-de-nuit";
        if (_flags.Contains(Flags.Tour)) yield return "guide";
        if (_flags.Contains(Flags.Contact)) yield return "recruteur";
        if (_flags.Contains(Flags.Chess)) yield return "echec-et-mat";
        if (_flags.Contains(Flags.Flawless)) yield return "sans-faute";
        if (_flags.Contains(Flags.Critical)) yield return "critique";
        foreach (var boss in Bestiary.All.Where(b => _bosses.Contains(b.Id)))
        {
            yield return boss.AchievementId;
        }
    }

    private Task SaveAsync()
    {
        var data = new SaveData([.. _visited], [.. _read], [.. _achievements], [.. _flags], VisitorName, [.. _bosses]);
        return browser.SetAsync(StorageKey, JsonSerializer.Serialize(data, SaveJsonContext.Default.SaveData));
    }
}
