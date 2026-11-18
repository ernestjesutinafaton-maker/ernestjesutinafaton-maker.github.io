using ErnestWorld.Game;

namespace ErnestWorld.Data;

/// <summary>Un succès à débloquer (badge).</summary>
public sealed record Achievement(string Id, Txt Name, Txt Description, string Icon);

/// <summary>Le rang du voyageur, qui monte avec l'XP.</summary>
public sealed record Level(int Number, Txt Title, int MinXp, int? NextXp)
{
    /// <summary>Avancement vers le rang suivant, entre 0 et 1.</summary>
    public double Progress(int xp) =>
        NextXp is int next ? Math.Clamp((xp - MinXp) / (double)(next - MinXp), 0, 1) : 1;
}

/// <summary>Les actions qui ne sont ni un lieu, ni un article, ni un boss, mais qui comptent.</summary>
public static class Flags
{
    public const string Subscribed = "abonne";
    public const string Night = "nuit";
    public const string Tour = "visite-guidee";
    public const string Contact = "contact";
    public const string Chess = "echecs";
    public const string Flawless = "sans-faute";
    public const string Critical = "critique";
}

/// <summary>Les règles du jeu : ce que rapporte chaque action, les rangs et les succès.</summary>
public static class Rules
{
    public const int XpPerPlace = 100;
    public const int XpPerPost = 150;
    public const int XpPerAchievement = 50;
    public const int XpSubscribe = 200;
    public const int XpTour = 150;

    private static Txt T(string fr, string en) => new(fr, en);

    private static readonly (int MinXp, Txt Title)[] RankTable =
    [
        (0, T("Voyageur", "Traveler")),
        (300, T("Explorateur", "Explorer")),
        (700, T("Éclaireur", "Scout")),
        (1200, T("Aventurier", "Adventurer")),
        (1900, T("Chevalier", "Knight")),
        (2700, "Champion"),
        (3600, T("Héros de l'île", "Island Hero")),
        (4600, T("Légende de l'île", "Island Legend")),
    ];

    public static Level LevelFor(int xp)
    {
        var index = Math.Max(0, Array.FindLastIndex(RankTable, l => xp >= l.MinXp));
        int? next = index + 1 < RankTable.Length ? RankTable[index + 1].MinXp : null;
        return new Level(index + 1, RankTable[index].Title, RankTable[index].MinXp, next);
    }

    /// <summary>Plus le rang est haut, plus on part au combat avec de cœurs et d'indices.</summary>
    public static (int Hearts, int Hints) BattleStats(int rank) =>
        (3 + (rank >= 3 ? 1 : 0) + (rank >= 6 ? 1 : 0),
         1 + (rank >= 2 ? 1 : 0) + (rank >= 5 ? 1 : 0));

    public static IReadOnlyList<Achievement> Achievements { get; } =
    [
        new("premier-pas", T("Premier pas", "First Steps"), T("Découvrir un premier lieu de l'île.", "Discover your first place on the island."), "chateau"),
        new("cartographe", T("Cartographe", "Cartographer"), T("Découvrir tous les lieux de l'île.", "Discover every place on the island."), "map"),
        new("lecteur", T("Lecteur", "Reader"), T("Lire un article du Journal jusqu'au bout.", "Read a Journal article to the end."), "page"),
        new("erudit", T("Érudit", "Scholar"), T("Lire tous les articles du Journal.", "Read every Journal article."), "book"),
        new("messager", T("Messager", "Messenger"), T("S'abonner à la newsletter au Pigeonnier.", "Subscribe to the newsletter at the Dovecote."), "pigeonnier"),
        new("oiseau-de-nuit", T("Oiseau de nuit", "Night Owl"), T("Faire tomber la nuit sur l'île.", "Bring night upon the island."), "moon"),
        new("guide", T("Guide de l'île", "Island Guide"), T("Suivre la visite guidée jusqu'au bout.", "Follow the guided tour to the end."), "play"),
        new("recruteur", T("Recruteur", "Recruiter"), T("Prendre contact avec Ernest depuis le Phare.", "Get in touch with Ernest from the Lighthouse."), "phare"),
        new("echec-et-mat", T("Échec et mat", "Checkmate"), T("Relever le défi aux échecs au Monument.", "Accept the chess challenge at the Monument."), "crown"),
        new("chasseur-de-bugs", T("Chasseur de bugs", "Bug Hunter"), T("Vaincre le Bug Rampant (niveau 1).", "Defeat the Crawling Bug (level 1)."), "bug"),
        new("tranche-tetes", T("Tranche-têtes", "Hydra Slayer"), T("Vaincre l'Hydre Hors-Ligne (niveau 2).", "Defeat the Offline Hydra (level 2)."), "wave"),
        new("briseur-de-golem", T("Briseur de golem", "Golem Breaker"), T("Vaincre le Golem du Réseau (niveau 3).", "Defeat the Network Golem (level 3)."), "cube"),
        new("pourfendeur-de-kraken", T("Pourfendeur de Kraken", "Kraken Slayer"), T("Vaincre le Kraken du Code Legacy (niveau 4).", "Defeat the Legacy Code Kraken (level 4)."), "anchor"),
        new("tueur-de-dragon", T("Tueur de dragon", "Dragon Slayer"), T("Vaincre le Dragon de la Dette Technique (boss final).", "Defeat the Technical Debt Dragon (final boss)."), "flame"),
        new("sans-faute", T("Sans une égratignure", "Not a Scratch"), T("Vaincre un boss sans perdre un seul cœur.", "Defeat a boss without losing a single heart."), "shield"),
        new("critique", T("Coup critique", "Critical Hit"), T("Enchaîner trois bonnes réponses en combat.", "Give three right answers in a row in battle."), "bolt"),
    ];
}
