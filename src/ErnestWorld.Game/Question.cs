namespace ErnestWorld.Game;

/// <summary>
/// Une question de combat, en français et en anglais. On écrit la bonne réponse et les mauvaises
/// séparément : le moteur mélange les choix à chaque combat.
/// </summary>
/// <param name="Prompt">L'énoncé.</param>
/// <param name="Answer">La bonne réponse.</param>
/// <param name="Wrong">Les mauvaises réponses (trois en général).</param>
/// <param name="Explanation">Affichée après la réponse, pour apprendre quelque chose.</param>
/// <param name="Code">Extrait de code à lire, s'il y en a un (identique dans les deux langues).</param>
/// <param name="HintPlace">Lieu de l'île où trouver la réponse (pour l'indice).</param>
/// <param name="Phase">1 = phase normale, 2 = phase enragée du boss final.</param>
public sealed record Question(
    Txt Prompt,
    Txt Answer,
    IReadOnlyList<Txt> Wrong,
    Txt Explanation,
    string? Code = null,
    string? HintPlace = null,
    int Phase = 1);

/// <summary>Une question telle qu'elle est posée : choix mélangés, certains éventuellement retirés par un indice.</summary>
public sealed class AskedQuestion
{
    private readonly HashSet<int> _removed = [];

    public AskedQuestion(Question source, IReadOnlyList<Txt> choices, int correctIndex)
    {
        Source = source;
        Choices = choices;
        CorrectIndex = correctIndex;
    }

    public Question Source { get; }
    public IReadOnlyList<Txt> Choices { get; }
    public int CorrectIndex { get; }

    /// <summary>Choix retirés par un indice.</summary>
    public IReadOnlySet<int> Removed => _removed;

    internal void Remove(int index) => _removed.Add(index);
}
