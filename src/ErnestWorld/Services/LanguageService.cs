using ErnestWorld.Game;

namespace ErnestWorld.Services;

/// <summary>
/// La langue du site (français ou anglais).
/// Ordre de choix : le lien (<c>?lang=en</c>), puis le choix enregistré, puis la langue du navigateur.
/// </summary>
public sealed class LanguageService(BrowserService browser)
{
    private const string StorageKey = "ernest-lang";

    public Lang Current { get; private set; } = Lang.Fr;
    public bool En => Current == Lang.En;

    /// <summary>Déclenché quand la langue change (MainLayout rafraîchit alors toute l'interface).</summary>
    public event Action? Changed;

    public string T(string fr, string en) => En ? en : fr;
    public string T(Txt text) => text.Get(Current);

    public async Task InitAsync(string uri)
    {
        var fromLink = Parse(QueryValue(uri, "lang"));
        var saved = Parse(await browser.GetAsync(StorageKey));
        var lang = fromLink ?? saved ?? (await browser.PrefersFrenchAsync() ? Lang.Fr : Lang.En);
        await ApplyAsync(lang, remember: fromLink is not null);
    }

    public Task SetAsync(Lang lang) => ApplyAsync(lang, remember: true);

    public Task ToggleAsync() => SetAsync(En ? Lang.Fr : Lang.En);

    private async Task ApplyAsync(Lang lang, bool remember)
    {
        var changed = lang != Current;
        Current = lang;
        if (remember)
        {
            await browser.SetAsync(StorageKey, Code(lang));
        }

        await browser.SetDocumentLangAsync(Code(lang));
        if (changed)
        {
            Changed?.Invoke();
        }
    }

    public static string Code(Lang lang) => lang == Lang.En ? "en" : "fr";

    private static Lang? Parse(string? value) => value?.Trim().ToLowerInvariant() switch
    {
        "en" => Lang.En,
        "fr" => Lang.Fr,
        _ => null,
    };

    private static string? QueryValue(string uri, string key)
    {
        foreach (var pair in new Uri(uri).Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = pair.Split('=', 2);
            if (parts.Length == 2 && parts[0] == key)
            {
                return Uri.UnescapeDataString(parts[1]);
            }
        }

        return null;
    }
}
