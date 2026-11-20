// ===========================================================================
//  Générateur du Journal
//  Lit les articles Markdown de wwwroot/posts et produit :
//   - posts/index.json : la liste des articles publiés (lue par le site) ;
//   - rss.xml          : le flux RSS, pour suivre le blog dans un lecteur ;
//   - sitemap.xml      : le plan du site, pour les moteurs de recherche.
//
//  Utilisation (depuis la racine du dépôt) :
//    dotnet run --project tools/ErnestWorld.Generator
//    dotnet run --project tools/ErnestWorld.Generator -- <dossier wwwroot> <url du site> [--drafts]
// ===========================================================================
using System.Globalization;
using System.Text.Json;
using System.Xml.Linq;
using ErnestWorld.Content;

var positional = args.Where(a => !a.StartsWith("--", StringComparison.Ordinal)).ToArray();
var wwwroot = Path.GetFullPath(positional.ElementAtOrDefault(0) ?? Path.Combine("src", "ErnestWorld", "wwwroot"));
var siteUrl = (positional.ElementAtOrDefault(1) ?? "https://ernestjesutinafaton-maker.github.io").TrimEnd('/');
var includeDrafts = args.Contains("--drafts");

var postsDir = Path.Combine(wwwroot, "posts");
if (!Directory.Exists(postsDir))
{
    Console.Error.WriteLine($"Dossier introuvable : {postsDir}");
    return 1;
}

var posts = new List<PostMeta>();
var errors = new List<string>();

// Les fichiers qui commencent par « _ » (modèles, notes) sont ignorés.
foreach (var file in Directory.EnumerateFiles(postsDir, "*.md").Order(StringComparer.Ordinal))
{
    var slug = Path.GetFileNameWithoutExtension(file);
    if (slug.StartsWith('_'))
    {
        continue;
    }

    try
    {
        var post = PostParser.Parse(slug, await File.ReadAllTextAsync(file));
        if (post.Draft && !includeDrafts)
        {
            Console.WriteLine($"  brouillon ignoré : {slug}");
            continue;
        }

        posts.Add(post);
    }
    catch (FormatException ex)
    {
        errors.Add($"{Path.GetFileName(file)} : {ex.Message}");
    }
}

if (errors.Count > 0)
{
    Console.Error.WriteLine("Articles invalides :");
    errors.ForEach(e => Console.Error.WriteLine("  - " + e));
    return 1;
}

posts = posts.OrderByDescending(p => p.Date).ThenBy(p => p.Slug, StringComparer.Ordinal).ToList();

// 1. Index lu par le site
var indexJson = JsonSerializer.Serialize(posts, ContentJsonContext.Default.ListPostMeta);
await File.WriteAllTextAsync(Path.Combine(postsDir, "index.json"), indexJson + Environment.NewLine);

// 2. Flux RSS 2.0
static string Rfc822(DateOnly date) =>
    date.ToDateTime(new TimeOnly(9, 0), DateTimeKind.Utc).ToString("r", CultureInfo.InvariantCulture);

var rss = new XDocument(
    new XDeclaration("1.0", "utf-8", null),
    new XElement("rss", new XAttribute("version", "2.0"),
        new XElement("channel",
            new XElement("title", "Le Journal d'Ernest"),
            new XElement("link", siteUrl + "/journal"),
            new XElement("description", "Le blog d'Ernest Afaton : projets, apprentissages et passions d'un étudiant développeur."),
            new XElement("language", "fr-FR"),
            posts.Select(p => new XElement("item",
                new XElement("title", p.Title),
                new XElement("link", $"{siteUrl}/journal/{p.Slug}"),
                new XElement("guid", $"{siteUrl}/journal/{p.Slug}"),
                new XElement("pubDate", Rfc822(p.Date)),
                new XElement("description", p.Summary),
                p.Tags.Select(t => new XElement("category", t)))))));
await File.WriteAllTextAsync(Path.Combine(wwwroot, "rss.xml"), rss.Declaration + Environment.NewLine + rss);

// 3. Plan du site
XNamespace sm = "http://www.sitemaps.org/schemas/sitemap/0.9";
// « / » : le portfolio classique (page d'accueil) ; « /jeu/ » : la version jeu (île en 3D) ;
// « /3d/ » : la version immersive (île modélisée dans Blender, parcourue au défilement).
var pages = new[] { "/", "/3d/", "/jeu/", "/journal" }
    .Select(path => new XElement(sm + "url", new XElement(sm + "loc", siteUrl + path)))
    .Concat(posts.Select(p => new XElement(sm + "url",
        new XElement(sm + "loc", $"{siteUrl}/journal/{p.Slug}"),
        new XElement(sm + "lastmod", p.Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)))));
var sitemap = new XDocument(new XDeclaration("1.0", "utf-8", null), new XElement(sm + "urlset", pages));
await File.WriteAllTextAsync(Path.Combine(wwwroot, "sitemap.xml"), sitemap.Declaration + Environment.NewLine + sitemap);

Console.WriteLine($"Journal généré : {posts.Count} article(s) publié(s).");
posts.ForEach(p => Console.WriteLine($"  {p.Date:yyyy-MM-dd}  {p.Slug}  ({p.ReadingMinutes} min)"));
return 0;
