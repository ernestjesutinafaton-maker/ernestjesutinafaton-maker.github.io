namespace ErnestWorld.Data;

/// <summary>Un succès à débloquer (badge).</summary>
public sealed record Achievement(string Id, string Name, string Description, string Icon);

/// <summary>Le rang du voyageur, qui monte avec l'XP.</summary>
public sealed record Level(int Number, string Title, int MinXp, int? NextXp)
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

    private static readonly (int MinXp, string Title)[] RankTable =
    [
        (0, "Voyageur"),
        (300, "Explorateur"),
        (700, "Éclaireur"),
        (1200, "Aventurier"),
        (1900, "Chevalier"),
        (2700, "Champion"),
        (3600, "Héros de l'île"),
        (4600, "Légende de l'île"),
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
        new("premier-pas", "Premier pas", "Découvrir un premier lieu de l'île.", "chateau"),
        new("cartographe", "Cartographe", "Découvrir tous les lieux de l'île.", "map"),
        new("lecteur", "Lecteur", "Lire un article du Journal jusqu'au bout.", "page"),
        new("erudit", "Érudit", "Lire tous les articles du Journal.", "book"),
        new("messager", "Messager", "S'abonner à la newsletter au Pigeonnier.", "pigeonnier"),
        new("oiseau-de-nuit", "Oiseau de nuit", "Faire tomber la nuit sur l'île.", "moon"),
        new("guide", "Guide de l'île", "Suivre la visite guidée jusqu'au bout.", "play"),
        new("recruteur", "Recruteur", "Prendre contact avec Ernest depuis le Phare.", "phare"),
        new("echec-et-mat", "Échec et mat", "Relever le défi aux échecs au Monument.", "crown"),
        new("chasseur-de-bugs", "Chasseur de bugs", "Vaincre le Bug Rampant (niveau 1).", "bug"),
        new("tranche-tetes", "Tranche-têtes", "Vaincre l'Hydre Hors-Ligne (niveau 2).", "wave"),
        new("briseur-de-golem", "Briseur de golem", "Vaincre le Golem du Réseau (niveau 3).", "cube"),
        new("pourfendeur-de-kraken", "Pourfendeur de Kraken", "Vaincre le Kraken du Code Legacy (niveau 4).", "anchor"),
        new("tueur-de-dragon", "Tueur de dragon", "Vaincre le Dragon de la Dette Technique (boss final).", "flame"),
        new("sans-faute", "Sans une égratignure", "Vaincre un boss sans perdre un seul cœur.", "shield"),
        new("critique", "Coup critique", "Enchaîner trois bonnes réponses en combat.", "bolt"),
    ];
}
