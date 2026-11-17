using System.Net.Http.Json;
using ErnestWorld.Content;
using Markdig;

namespace ErnestWorld.Services;

/// <summary>Un article prêt à afficher.</summary>
public sealed record Post(PostMeta Meta, string Html);

/// <summary>
/// Le moteur du Journal : lit la liste des articles (posts/index.json, produite par le
/// générateur), télécharge un article Markdown et le transforme en HTML avec Markdig.
/// </summary>
public sealed class BlogService(HttpClient http, GameState game)
{
    private static readonly MarkdownPipeline Pipeline = new MarkdownPipelineBuilder()
        .UseAdvancedExtensions()
        .Build();

    private Task<IReadOnlyList<PostMeta>>? _posts;
    private readonly Dictionary<string, Post> _cache = [];

    /// <summary>Tous les articles publiés, du plus récent au plus ancien.</summary>
    public Task<IReadOnlyList<PostMeta>> GetPostsAsync() => _posts ??= LoadIndexAsync();

    private async Task<IReadOnlyList<PostMeta>> LoadIndexAsync()
    {
        try
        {
            var posts = await http.GetFromJsonAsync("posts/index.json", ContentJsonContext.Default.ListPostMeta) ?? [];
            await game.SetKnownPostsAsync(posts.Select(p => p.Slug));
            return posts;
        }
        catch (HttpRequestException)
        {
            _posts = null; // on réessaiera à la prochaine demande
            return [];
        }
    }

    /// <summary>Un article complet, ou <c>null</c> s'il n'existe pas.</summary>
    public async Task<Post?> GetPostAsync(string slug)
    {
        if (_cache.TryGetValue(slug, out var cached))
        {
            return cached;
        }

        var meta = (await GetPostsAsync()).FirstOrDefault(p => p.Slug == slug);
        if (meta is null)
        {
            return null;
        }

        var markdown = await http.GetStringAsync($"posts/{slug}.md");
        var (_, body) = FrontMatter.Split(markdown);
        var post = new Post(meta, Markdown.ToHtml(body, Pipeline));
        _cache[slug] = post;
        return post;
    }

    /// <summary>L'article précédent et le suivant dans la liste.</summary>
    public async Task<(PostMeta? Newer, PostMeta? Older)> GetNeighboursAsync(string slug)
    {
        var posts = await GetPostsAsync();
        var list = posts.ToList();
        var index = list.FindIndex(p => p.Slug == slug);
        if (index < 0)
        {
            return (null, null);
        }

        return (index > 0 ? list[index - 1] : null, index + 1 < list.Count ? list[index + 1] : null);
    }
}
