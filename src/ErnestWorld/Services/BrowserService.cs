using Microsoft.AspNetCore.Components;
using Microsoft.JSInterop;

namespace ErnestWorld.Services;

/// <summary>
/// Accès aux fonctions du navigateur (stockage local, presse-papiers, formulaires,
/// suivi de lecture) via le module JavaScript <c>js/interop.js</c>.
/// </summary>
public sealed class BrowserService(IJSRuntime js) : IAsyncDisposable
{
    private Task<IJSObjectReference>? _module;

    private Task<IJSObjectReference> Module =>
        _module ??= js.InvokeAsync<IJSObjectReference>("import", "./js/interop.js").AsTask();

    public async Task<string?> GetAsync(string key)
    {
        try
        {
            return await (await Module).InvokeAsync<string?>("storageGet", key);
        }
        catch (JSException)
        {
            return null;
        }
    }

    public async Task SetAsync(string key, string value)
    {
        try
        {
            await (await Module).InvokeAsync<bool>("storageSet", key, value);
        }
        catch (JSException)
        {
            // Stockage indisponible (navigation privée…) : la progression ne sera simplement pas gardée.
        }
    }

    public async Task<bool> CopyAsync(string text) => await (await Module).InvokeAsync<bool>("copyText", text);

    public async Task OpenAsync(string url) => await (await Module).InvokeVoidAsync("openUrl", url);

    public async Task SubmitAsync(ElementReference form) => await (await Module).InvokeVoidAsync("submitForm", form);

    public async Task ScrollToTopAsync(ElementReference element) => await (await Module).InvokeVoidAsync("scrollToTop", element);

    public async Task<bool> IsSmallScreenAsync() => await (await Module).InvokeAsync<bool>("isSmallScreen");

    /// <summary>Le navigateur est-il réglé en français ?</summary>
    public async Task<bool> PrefersFrenchAsync()
    {
        try
        {
            return await (await Module).InvokeAsync<bool>("prefersFrench");
        }
        catch (JSException)
        {
            return true;
        }
    }

    /// <summary>Met à jour l'attribut lang de la page (lecteurs d'écran, traduction automatique).</summary>
    public async Task SetDocumentLangAsync(string code) => await (await Module).InvokeVoidAsync("setDocumentLang", code);

    public async Task PrintAsync() => await (await Module).InvokeVoidAsync("printPage");

    /// <summary>Suit la lecture d'un article. Le composant reçoit <c>OnReadComplete</c> une fois l'article lu.</summary>
    public async Task<IJSObjectReference> WatchReadingAsync<T>(ElementReference scroller, ElementReference bar, DotNetObjectReference<T> listener)
        where T : class =>
        await (await Module).InvokeAsync<IJSObjectReference>("watchReading", scroller, bar, listener);

    public async ValueTask DisposeAsync()
    {
        if (_module is { IsCompletedSuccessfully: true })
        {
            try
            {
                await (await _module).DisposeAsync();
            }
            catch (JSDisconnectedException)
            {
            }
        }
    }
}
