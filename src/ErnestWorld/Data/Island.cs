using ErnestWorld.Components.Places;

namespace ErnestWorld.Data;

/// <summary>
/// La carte de l'île. L'ordre de la liste est celui de la barre des lieux,
/// des boutons « précédent / suivant » et de la visite guidée.
/// </summary>
public static class Island
{
    public static IReadOnlyList<Place> Places { get; } =
    [
        new("chateau", "Le Château", "Château", "Centre de l'île · À propos", "Entrer dans le Château", 0, 0, typeof(Chateau)),
        new("forge", "La Forge", "Forge", "Compétences", "Allumer la Forge", 3, -3, typeof(Forge)),
        new("qg", "Le QG MyDil", "QG MyDil", "Expérience · avril - juin 2026", "Rejoindre le QG MyDil", 0, -3, typeof(Qg)),
        new("academie", "L'Académie", "Formation", "Formation", "S'inscrire à l'Académie", -3, 3, typeof(Academie)),
        new("camp", "Le Camp d'entraînement", "Projets école", "Projets de formation", "S'entraîner au Camp", -3, 0, typeof(Camp)),
        new("banque", "La Banque ÉcoPay", "ÉcoPay", "Projet personnel · SaaS", "Ouvrir la Banque ÉcoPay", 3, 0, typeof(Banque)),
        new("marche", "Le Marché Boutik", "Boutik", "Projet personnel · mobile, bureau, web", "Visiter le Marché Boutik", 0, 3, typeof(Marche)),
        new("observatoire", "L'Observatoire", "Metrics AI", "Projet personnel · IA", "Grimper à l'Observatoire", 3, -6, typeof(Observatoire)),
        new("arene", "L'Arène Cascade", "Arène", "Projet personnel · jeu éducatif", "Combattre dans l'Arène", 3, 3, typeof(Arene)),
        new("bibliotheque", "La Bibliothèque", "readme-start", "Projet personnel · outil en ligne de commande", "Consulter la Bibliothèque", -3, 6, typeof(Bibliotheque)),
        new("ruche", "La Ruche", "HiveTown", "Projet personnel · en conception", "Inspecter le chantier de la Ruche", 6, -3, typeof(Ruche)),
        new("radio", "La Tour Radio", "ShadowCom", "Projet personnel · web", "Capter la Tour Radio", -3, -3, typeof(Radio)),
        new("scriptorium", "Le Scriptorium", "Journal", "Blog · le Journal d'Ernest", "Lire au Scriptorium", 0, 6, typeof(Scriptorium)),
        new("pigeonnier", "Le Pigeonnier", "Newsletter", "Newsletter", "Passer au Pigeonnier", 6, 0, typeof(Pigeonnier)),
        new("monument", "Le Monument", "Trophées", "Distinctions et passions", "Contempler le Monument", -6, 3, typeof(Monument)),
        new("phare", "Le Phare", "Contact", "Quête finale · Contact", "Quête finale : recruter Ernest au Phare", -8, 3, typeof(Phare), IsFinal: true),
    ];

    /// <summary>Les lieux ordinaires (tous sauf la quête finale).</summary>
    public static IEnumerable<Place> Regular => Places.Where(p => !p.IsFinal);

    public static Place? Find(string? id) => Places.FirstOrDefault(p => p.Id == id);

    /// <summary>Le lieu situé <paramref name="offset"/> crans plus loin, en boucle.</summary>
    public static Place Step(string? fromId, int offset)
    {
        var index = Places.ToList().FindIndex(p => p.Id == fromId);
        var next = ((index < 0 ? (offset > 0 ? -1 : 0) : index) + offset) % Places.Count;
        return Places[next < 0 ? next + Places.Count : next];
    }

    public static IEnumerable<PlaceDto> ForWorld() =>
        Places.Select(p => new PlaceDto(p.Id, p.Short, p.Q, p.R, Icons.Path(p.Id)));
}
