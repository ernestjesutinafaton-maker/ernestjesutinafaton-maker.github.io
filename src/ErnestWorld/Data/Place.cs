namespace ErnestWorld.Data;

/// <summary>
/// Un lieu de l'île : un bâtiment en 3D et le panneau qui s'ouvre quand on le visite.
/// </summary>
/// <param name="Id">Identifiant, partagé avec le moteur 3D (world.js).</param>
/// <param name="Name">Nom complet affiché dans le panneau.</param>
/// <param name="Short">Nom court affiché sur l'île et dans la barre des lieux.</param>
/// <param name="Kicker">Petite ligne au-dessus du titre du panneau.</param>
/// <param name="Quest">Intitulé de la quête dans le journal de quêtes.</param>
/// <param name="Q">Coordonnée hexagonale (axe q).</param>
/// <param name="R">Coordonnée hexagonale (axe r).</param>
/// <param name="Content">Composant Razor affiché dans le panneau.</param>
/// <param name="IsFinal">La quête finale ne se débloque qu'une fois tous les autres lieux découverts.</param>
public sealed record Place(
    string Id,
    string Name,
    string Short,
    string Kicker,
    string Quest,
    int Q,
    int R,
    Type Content,
    bool IsFinal = false);

/// <summary>Ce que le moteur 3D a besoin de savoir d'un lieu.</summary>
public sealed record PlaceDto(string Id, string Label, int Q, int R, string Icon);
