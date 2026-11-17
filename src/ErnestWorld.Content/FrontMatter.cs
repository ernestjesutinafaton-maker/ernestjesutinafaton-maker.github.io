namespace ErnestWorld.Content;

/// <summary>
/// Lit l'en-tête placé en haut d'un fichier Markdown, entre deux lignes « --- » :
/// <code>
/// ---
/// title: Mon article
/// date: 2026-11-17
/// tags: [blog, csharp]
/// ---
/// </code>
/// Volontairement simple : une paire « clé: valeur » par ligne, et des listes entre crochets.
/// </summary>
public static class FrontMatter
{
    private const string Fence = "---";

    /// <summary>Sépare l'en-tête (clés en minuscules) et le corps Markdown.</summary>
    public static (IReadOnlyDictionary<string, string> Fields, string Body) Split(string markdown)
    {
        ArgumentNullException.ThrowIfNull(markdown);

        var text = markdown.Replace("\r\n", "\n").TrimStart('﻿');
        var fields = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        if (!text.StartsWith(Fence + "\n", StringComparison.Ordinal))
        {
            return (fields, text);
        }

        var end = text.IndexOf("\n" + Fence, Fence.Length, StringComparison.Ordinal);
        if (end < 0)
        {
            throw new FormatException("L'en-tête de l'article commence par « --- » mais n'est jamais refermé.");
        }

        var header = text[(Fence.Length + 1)..end];
        foreach (var rawLine in header.Split('\n'))
        {
            var line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith('#'))
            {
                continue;
            }

            var colon = line.IndexOf(':');
            if (colon <= 0)
            {
                throw new FormatException($"Ligne d'en-tête invalide : « {line} ». Format attendu : « clé: valeur ».");
            }

            var key = line[..colon].Trim();
            var value = Unquote(line[(colon + 1)..].Trim());
            fields[key] = value;
        }

        var bodyStart = end + 1 + Fence.Length;
        var body = bodyStart < text.Length ? text[bodyStart..].TrimStart('\n') : string.Empty;
        return (fields, body);
    }

    /// <summary>Lit une liste « [a, b, c] » (ou une valeur seule) en éléments nettoyés.</summary>
    public static IReadOnlyList<string> ParseList(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return [];
        }

        var inner = value.Trim();
        if (inner.StartsWith('[') && inner.EndsWith(']'))
        {
            inner = inner[1..^1];
        }

        return inner
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(Unquote)
            .Where(item => item.Length > 0)
            .ToArray();
    }

    private static string Unquote(string value)
    {
        if (value.Length >= 2 &&
            ((value[0] == '"' && value[^1] == '"') || (value[0] == '\'' && value[^1] == '\'')))
        {
            return value[1..^1];
        }

        return value;
    }
}
