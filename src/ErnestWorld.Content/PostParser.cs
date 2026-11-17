using System.Globalization;
using System.Text.RegularExpressions;

namespace ErnestWorld.Content;

/// <summary>Transforme un fichier Markdown du Journal en <see cref="PostMeta"/>.</summary>
public static partial class PostParser
{
    /// <summary>Vitesse de lecture moyenne utilisée pour estimer la durée d'un article.</summary>
    public const int WordsPerMinute = 200;

    /// <summary>Lit l'en-tête d'un article. Lève une <see cref="FormatException"/> si un champ obligatoire manque.</summary>
    public static PostMeta Parse(string slug, string markdown)
    {
        if (!IsValidSlug(slug))
        {
            throw new FormatException($"Nom de fichier invalide : « {slug} ». Utiliser des minuscules, des chiffres et des tirets.");
        }

        var (fields, body) = FrontMatter.Split(markdown);

        var title = Required(fields, "title", slug);
        var dateText = Required(fields, "date", slug);
        if (!DateOnly.TryParseExact(dateText, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var date))
        {
            throw new FormatException($"Article « {slug} » : la date doit être au format AAAA-MM-JJ (reçu « {dateText} »).");
        }

        fields.TryGetValue("summary", out var summary);
        fields.TryGetValue("tags", out var tags);
        fields.TryGetValue("draft", out var draft);

        return new PostMeta(
            Slug: slug,
            Title: title,
            Date: date,
            Summary: summary ?? string.Empty,
            Tags: FrontMatter.ParseList(tags),
            ReadingMinutes: EstimateReadingMinutes(body),
            Draft: string.Equals(draft, "true", StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>Estime le temps de lecture d'un texte Markdown (au moins une minute).</summary>
    public static int EstimateReadingMinutes(string markdownBody)
    {
        var withoutCode = CodeBlock().Replace(markdownBody ?? string.Empty, " ");
        var words = Word().Count(withoutCode);
        return Math.Max(1, (int)Math.Round(words / (double)WordsPerMinute, MidpointRounding.AwayFromZero));
    }

    /// <summary>Un slug ne contient que des minuscules, des chiffres et des tirets.</summary>
    public static bool IsValidSlug(string slug) => !string.IsNullOrEmpty(slug) && Slug().IsMatch(slug);

    private static string Required(IReadOnlyDictionary<string, string> fields, string key, string slug)
    {
        if (fields.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value))
        {
            return value;
        }

        throw new FormatException($"Article « {slug} » : le champ « {key} » est obligatoire dans l'en-tête.");
    }

    [GeneratedRegex(@"```.*?```", RegexOptions.Singleline)]
    private static partial Regex CodeBlock();

    [GeneratedRegex(@"[\p{L}\p{N}'’-]+")]
    private static partial Regex Word();

    [GeneratedRegex(@"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    private static partial Regex Slug();
}
