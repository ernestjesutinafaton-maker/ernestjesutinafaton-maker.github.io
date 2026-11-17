using ErnestWorld.Content;

namespace ErnestWorld.Content.Tests;

public class PostParserTests
{
    private const string Sample = """
        ---
        title: "Bienvenue sur mon île"
        date: 2026-11-17
        summary: Un portfolio qui se visite comme un jeu.
        tags: [portfolio, 3d, csharp]
        ---
        # Bonjour

        Du texte.
        """;

    [Fact]
    public void Parse_lit_tous_les_champs()
    {
        var post = PostParser.Parse("bienvenue", Sample);

        Assert.Equal("bienvenue", post.Slug);
        Assert.Equal("Bienvenue sur mon île", post.Title);
        Assert.Equal(new DateOnly(2026, 11, 17), post.Date);
        Assert.Equal("Un portfolio qui se visite comme un jeu.", post.Summary);
        Assert.Equal(["portfolio", "3d", "csharp"], post.Tags);
        Assert.False(post.Draft);
        Assert.Equal(1, post.ReadingMinutes);
    }

    [Fact]
    public void Split_separe_en_tete_et_corps()
    {
        var (fields, body) = FrontMatter.Split(Sample);

        Assert.Equal("2026-11-17", fields["DATE"]);
        Assert.StartsWith("# Bonjour", body);
    }

    [Fact]
    public void Split_accepte_les_fins_de_ligne_Windows()
    {
        var (fields, body) = FrontMatter.Split("---\r\ntitle: A\r\n---\r\nTexte");

        Assert.Equal("A", fields["title"]);
        Assert.Equal("Texte", body);
    }

    [Fact]
    public void Un_brouillon_est_detecte()
    {
        var post = PostParser.Parse("brouillon", "---\ntitle: T\ndate: 2026-01-02\ndraft: true\n---\nx");

        Assert.True(post.Draft);
    }

    [Fact]
    public void Un_titre_manquant_est_signale()
    {
        var ex = Assert.Throws<FormatException>(() => PostParser.Parse("sans-titre", "---\ndate: 2026-01-02\n---\nx"));

        Assert.Contains("title", ex.Message);
    }

    [Fact]
    public void Une_date_mal_formee_est_signalee()
    {
        Assert.Throws<FormatException>(() => PostParser.Parse("date", "---\ntitle: T\ndate: 17/11/2026\n---\nx"));
    }

    [Fact]
    public void Un_en_tete_non_referme_est_signale()
    {
        Assert.Throws<FormatException>(() => FrontMatter.Split("---\ntitle: T\nPas de fin"));
    }

    [Theory]
    [InlineData("bienvenue", true)]
    [InlineData("nas-auto-heberge-2026", true)]
    [InlineData("Majuscule", false)]
    [InlineData("double--tiret", false)]
    [InlineData("espace interdit", false)]
    [InlineData("", false)]
    public void Les_slugs_sont_valides(string slug, bool attendu)
    {
        Assert.Equal(attendu, PostParser.IsValidSlug(slug));
    }

    [Fact]
    public void Le_temps_de_lecture_ignore_le_code_et_vaut_au_moins_une_minute()
    {
        var mots = string.Join(' ', Enumerable.Repeat("mot", 450));
        var texte = mots + "\n```\n" + string.Join(' ', Enumerable.Repeat("code", 5000)) + "\n```";

        Assert.Equal(2, PostParser.EstimateReadingMinutes(texte));
        Assert.Equal(1, PostParser.EstimateReadingMinutes("court"));
    }

    [Fact]
    public void ParseList_accepte_une_valeur_seule_ou_vide()
    {
        Assert.Equal(["seul"], FrontMatter.ParseList("seul"));
        Assert.Empty(FrontMatter.ParseList(""));
        Assert.Equal(["a", "b"], FrontMatter.ParseList("['a', \"b\"]"));
    }
}
