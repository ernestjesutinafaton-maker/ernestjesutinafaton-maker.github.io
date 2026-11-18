using ErnestWorld.Game;
using ErnestWorld.Services;

namespace ErnestWorld.Data;

/// <summary>Où en est un niveau de la campagne.</summary>
public enum LevelState
{
    /// <summary>Le boss du niveau précédent n'est pas encore vaincu.</summary>
    Locked,

    /// <summary>Niveau ouvert : il reste des objectifs.</summary>
    InProgress,

    /// <summary>Objectifs remplis : le boss est réveillé.</summary>
    BossReady,

    /// <summary>Boss vaincu.</summary>
    Completed,
}

/// <summary>Un objectif de niveau (découvrir un lieu, lire des articles…).</summary>
public sealed record Objective(Txt Label, Func<GameState, bool> IsDone, string? PlaceId = null, string? Href = null);

/// <summary>Un niveau de la campagne, gardé par un boss.</summary>
public sealed record CampaignLevel(int Number, Txt Name, Txt Story, string BossId, IReadOnlyList<Objective> Objectives)
{
    public BossDefinition Boss => Bestiary.Find(BossId)!;
}

/// <summary>
/// La campagne en 5 niveaux. Les lieux restent toujours visitables (c'est un portfolio !),
/// mais chaque niveau demande d'en découvrir certains avant de réveiller son boss.
/// </summary>
public static class Campaign
{
    private static Txt T(string fr, string en) => new(fr, en);

    public static IReadOnlyList<CampaignLevel> Levels { get; } =
    [
        new(1, T("L'Arrivée", "The Arrival"),
            T("Tu poses le pied sur l'île. Apprends qui est Ernest avant d'affronter le premier gardien.",
              "You set foot on the island. Learn who Ernest is before facing the first guardian."),
            "bug", [Visit("chateau"), Visit("forge"), Visit("academie")]),
        new(2, T("Les Bâtisseurs", "The Builders"),
            T("Les projets d'Ernest forment la ville. L'Hydre ne craint que ceux qui les connaissent.",
              "Ernest's projects make up the town. The Hydra only fears those who know them."),
            "hydre", [Visit("banque"), Visit("marche"), Visit("observatoire"), Visit("arene")]),
        new(3, T("Le Réseau", "The Network"),
            T("Sous l'île court un réseau de câbles et de serveurs. Le Golem en garde l'entrée.",
              "Beneath the island runs a web of cables and servers. The Golem guards the entrance."),
            "golem", [Visit("qg"), Visit("camp"), Visit("radio")]),
        new(4, T("Le Savoir", "The Knowledge"),
            T("Les livres, les ruches et les parchemins cachent les secrets du code. Le Kraken rôde au large.",
              "Books, hives and scrolls hold the secrets of code. The Kraken lurks offshore."),
            "kraken", [Visit("scriptorium"), Visit("bibliotheque"), Visit("ruche"), Read(1)]),
        new(5, T("La Tempête", "The Storm"),
            T("Le ciel s'assombrit. Au sommet de la montagne, le Dragon de la Dette Technique se réveille.",
              "The sky darkens. At the top of the mountain, the Technical Debt Dragon awakens."),
            "dragon", [Visit("pigeonnier"), Visit("monument"), Read(2)]),
    ];

    private static Objective Visit(string placeId)
    {
        var name = Island.Find(placeId)!.Name;
        return new(T($"Découvrir {LowerFirst(name.Fr)}", $"Discover {LowerFirst(name.En)}"), g => g.HasVisited(placeId), PlaceId: placeId);
    }

    private static Objective Read(int count) =>
        new(count == 1
                ? T("Lire un article du Journal", "Read a Journal article")
                : T($"Lire {count} articles du Journal", $"Read {count} Journal articles"),
            g => g.ReadCount >= count, Href: "journal");

    /// <summary>« Le Château » → « le Château », « The Castle » → « the Castle », mais « MyDil HQ » reste tel quel.</summary>
    private static string LowerFirst(string text) =>
        text.StartsWith("Le ") || text.StartsWith("La ") || text.StartsWith("L'") || text.StartsWith("The ")
            ? char.ToLowerInvariant(text[0]) + text[1..]
            : text;

    public static CampaignLevel? ForBoss(string? bossId) => Levels.FirstOrDefault(l => l.BossId == bossId);

    public static LevelState StateOf(CampaignLevel level, GameState game)
    {
        if (game.HasDefeated(level.BossId))
        {
            return LevelState.Completed;
        }

        var unlocked = level.Number == 1 || game.HasDefeated(Levels[level.Number - 2].BossId);
        if (!unlocked)
        {
            return LevelState.Locked;
        }

        return level.Objectives.All(o => o.IsDone(game)) ? LevelState.BossReady : LevelState.InProgress;
    }

    /// <summary>Le niveau en cours (ou null si la campagne est terminée).</summary>
    public static CampaignLevel? Current(GameState game) =>
        Levels.FirstOrDefault(l => StateOf(l, game) is LevelState.InProgress or LevelState.BossReady);

    public static bool IsComplete(GameState game) => Levels.All(l => game.HasDefeated(l.BossId));

    /// <summary>Peut-on combattre ce boss maintenant (premier combat ou revanche) ?</summary>
    public static bool CanFight(string bossId, GameState game) =>
        ForBoss(bossId) is { } level && StateOf(level, game) is LevelState.BossReady or LevelState.Completed;

    /// <summary>L'état des boss pour le moteur 3D : « locked », « available » ou « defeated ».</summary>
    public static IEnumerable<BossDto> ForWorld(GameState game, Lang lang) =>
        Levels.Select(l => new BossDto(l.BossId, l.Boss.Name.Get(lang), StateOf(l, game) switch
        {
            LevelState.Completed => "defeated",
            LevelState.BossReady => "available",
            _ => "locked",
        }));

    /// <summary>Icône de chaque boss dans l'interface.</summary>
    public static string IconOf(string bossId) => bossId switch
    {
        "bug" => "bug",
        "hydre" => "wave",
        "golem" => "cube",
        "kraken" => "anchor",
        "dragon" => "flame",
        _ => "skull",
    };
}

/// <summary>Ce que le moteur 3D doit savoir d'un boss.</summary>
public sealed record BossDto(string Id, string Label, string State);

/// <summary>Les petits mots affichés par le moteur 3D sur les étiquettes.</summary>
public sealed record WorldStrings(string Boss, string Defeated)
{
    public static WorldStrings For(Lang lang) => lang == Lang.En ? new("Boss", "defeated") : new("Boss", "vaincu");
}
