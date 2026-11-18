using ErnestWorld.Components.Places;
using ErnestWorld.Game;

namespace ErnestWorld.Data;

/// <summary>
/// La carte de l'île. L'ordre de la liste est celui de la barre des lieux,
/// des boutons « précédent / suivant » et de la visite guidée.
/// </summary>
public static class Island
{
    private static Txt T(string fr, string en) => new(fr, en);

    public static IReadOnlyList<Place> Places { get; } =
    [
        new("chateau", T("Le Château", "The Castle"), T("Château", "Castle"),
            T("Centre de l'île · À propos", "Island center · About"), T("Entrer dans le Château", "Enter the Castle"), 0, 0, typeof(Chateau)),
        new("forge", T("La Forge", "The Forge"), T("Forge", "Forge"),
            T("Compétences", "Skills"), T("Allumer la Forge", "Light the Forge"), 3, -3, typeof(Forge)),
        new("qg", T("Le QG MyDil", "MyDil HQ"), T("QG MyDil", "MyDil HQ"),
            T("Expérience · avril - juin 2026", "Experience · April - June 2026"), T("Rejoindre le QG MyDil", "Join MyDil HQ"), 0, -3, typeof(Qg)),
        new("academie", T("L'Académie", "The Academy"), T("Formation", "Education"),
            T("Formation", "Education"), T("S'inscrire à l'Académie", "Enroll at the Academy"), -3, 3, typeof(Academie)),
        new("camp", T("Le Camp d'entraînement", "The Training Camp"), T("Projets école", "School projects"),
            T("Projets de formation", "School projects"), T("S'entraîner au Camp", "Train at the Camp"), -3, 0, typeof(Camp)),
        new("banque", T("La Banque ÉcoPay", "The ÉcoPay Bank"), "ÉcoPay",
            T("Projet personnel · SaaS", "Personal project · SaaS"), T("Ouvrir la Banque ÉcoPay", "Open the ÉcoPay Bank"), 3, 0, typeof(Banque)),
        new("marche", T("Le Marché Boutik", "The Boutik Market"), "Boutik",
            T("Projet personnel · mobile, bureau, web", "Personal project · mobile, desktop, web"), T("Visiter le Marché Boutik", "Visit the Boutik Market"), 0, 3, typeof(Marche)),
        new("observatoire", T("L'Observatoire", "The Observatory"), "Metrics AI",
            T("Projet personnel · IA", "Personal project · AI"), T("Grimper à l'Observatoire", "Climb the Observatory"), 3, -6, typeof(Observatoire)),
        new("arene", T("L'Arène Cascade", "The Cascade Arena"), T("Arène", "Arena"),
            T("Projet personnel · jeu éducatif", "Personal project · educational game"), T("Combattre dans l'Arène", "Fight in the Arena"), 3, 3, typeof(Arene)),
        new("bibliotheque", T("La Bibliothèque", "The Library"), "readme-start",
            T("Projet personnel · outil en ligne de commande", "Personal project · command-line tool"), T("Consulter la Bibliothèque", "Consult the Library"), -3, 6, typeof(Bibliotheque)),
        new("ruche", T("La Ruche", "The Hive"), "HiveTown",
            T("Projet personnel · en conception", "Personal project · in design"), T("Inspecter le chantier de la Ruche", "Inspect the Hive construction site"), 6, -3, typeof(Ruche)),
        new("radio", T("La Tour Radio", "The Radio Tower"), "ShadowCom",
            T("Projet personnel · web", "Personal project · web"), T("Capter la Tour Radio", "Tune in at the Radio Tower"), -3, -3, typeof(Radio)),
        new("scriptorium", T("Le Scriptorium", "The Scriptorium"), T("Journal", "Journal"),
            T("Blog · le Journal d'Ernest", "Blog · Ernest's Journal"), T("Lire au Scriptorium", "Read at the Scriptorium"), 0, 6, typeof(Scriptorium)),
        new("pigeonnier", T("Le Pigeonnier", "The Dovecote"), "Newsletter",
            "Newsletter", T("Passer au Pigeonnier", "Stop by the Dovecote"), 6, 0, typeof(Pigeonnier)),
        new("monument", T("Le Monument", "The Monument"), T("Trophées", "Trophies"),
            T("Distinctions et passions", "Awards and passions"), T("Contempler le Monument", "Admire the Monument"), -6, 3, typeof(Monument)),
        new("phare", T("Le Phare", "The Lighthouse"), "Contact",
            T("Quête finale · Contact", "Final quest · Contact"), T("Quête finale : recruter Ernest au Phare", "Final quest: recruit Ernest at the Lighthouse"), -8, 3, typeof(Phare), IsFinal: true),
    ];

    /// <summary>Les lieux ordinaires (tous sauf le Phare).</summary>
    public static IEnumerable<Place> Regular => Places.Where(p => !p.IsFinal);

    public static Place? Find(string? id) => Places.FirstOrDefault(p => p.Id == id);

    /// <summary>Le lieu situé <paramref name="offset"/> crans plus loin, en boucle.</summary>
    public static Place Step(string? fromId, int offset)
    {
        var index = Places.ToList().FindIndex(p => p.Id == fromId);
        var next = ((index < 0 ? (offset > 0 ? -1 : 0) : index) + offset) % Places.Count;
        return Places[next < 0 ? next + Places.Count : next];
    }

    public static IEnumerable<PlaceDto> ForWorld(Lang lang) =>
        Places.Select(p => new PlaceDto(p.Id, p.Short.Get(lang), p.Q, p.R, Icons.Path(p.Id)));
}
