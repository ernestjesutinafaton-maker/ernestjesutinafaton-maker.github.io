namespace ErnestWorld.Content;

/// <summary>
/// Les informations d'un article du Journal, lues dans l'en-tête (front matter) du fichier Markdown.
/// </summary>
/// <param name="Slug">Identifiant de l'article dans l'adresse : /journal/{slug}. C'est le nom du fichier sans « .md ».</param>
/// <param name="Title">Titre affiché.</param>
/// <param name="Date">Date de publication.</param>
/// <param name="Summary">Résumé d'une ou deux phrases, affiché dans la liste des articles.</param>
/// <param name="Tags">Thèmes de l'article, pour filtrer.</param>
/// <param name="ReadingMinutes">Temps de lecture estimé, en minutes.</param>
/// <param name="Draft">Un brouillon n'est pas publié.</param>
public sealed record PostMeta(
    string Slug,
    string Title,
    DateOnly Date,
    string Summary,
    IReadOnlyList<string> Tags,
    int ReadingMinutes,
    bool Draft = false);
