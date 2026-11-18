using ErnestWorld.Data;
using Microsoft.AspNetCore.Components;
using Microsoft.JSInterop;

namespace ErnestWorld.Services;

/// <summary>
/// Le pont entre le C# et le moteur 3D (wwwroot/js/world.js).
/// Le C# décide (quel lieu ouvrir, quel boss combattre, jour ou nuit…), le JavaScript dessine et joue les sons.
/// </summary>
public sealed class WorldService(IJSRuntime js) : IAsyncDisposable
{
    private IJSObjectReference? _module;

    public bool IsReady => _module is not null;

    public async Task InitAsync<T>(
        ElementReference canvas,
        ElementReference labels,
        DotNetObjectReference<T> listener,
        IEnumerable<PlaceDto> places,
        IEnumerable<string> visited,
        IEnumerable<BossDto> bosses,
        WorldStrings strings)
        where T : class
    {
        _module = await js.InvokeAsync<IJSObjectReference>("import", "./js/world.js");
        await _module.InvokeVoidAsync("init", canvas, labels, listener, places.ToArray(), visited.ToArray(), bosses.ToArray(), strings);
    }

    /// <summary>Change la langue des étiquettes 3D.</summary>
    public ValueTask SetLanguageAsync(IEnumerable<PlaceDto> places, IEnumerable<BossDto> bosses, WorldStrings strings) =>
        CallAsync("setLanguage", places.ToArray(), bosses.ToArray(), strings);

    // Exploration
    public ValueTask EnterAsync() => CallAsync("enter");
    public ValueTask FocusAsync(string placeId) => CallAsync("focusPlace", placeId);
    public ValueTask ClearFocusAsync() => CallAsync("clearFocus");
    public ValueTask HomeAsync() => CallAsync("home");
    public ValueTask SetNightAsync(bool night) => CallAsync("setNight", night);
    public ValueTask SetPausedAsync(bool paused) => CallAsync("setPaused", paused);
    public ValueTask ReleasePigeonAsync() => CallAsync("releasePigeon");
    public ValueTask AttachMinimapAsync(ElementReference canvas) => CallAsync("attachMinimap", canvas);

    // Les tableaux sont passés comme UN argument (sinon C# les étalerait en plusieurs arguments).
    public ValueTask SetVisitedAsync(IEnumerable<string> visited) => CallAsync("setVisited", (object)visited.ToArray());
    public ValueTask SetBossesAsync(IEnumerable<BossDto> bosses) => CallAsync("setBosses", (object)bosses.ToArray());

    // Combat
    public ValueTask BattleStartAsync(string bossId) => CallAsync("battleStart", bossId);
    public ValueTask BossHitAsync(string bossId, bool critical, double hpRatio) => CallAsync("bossHit", bossId, critical, hpRatio);
    public ValueTask BossAttackAsync(string bossId) => CallAsync("bossAttack", bossId);
    public ValueTask BossEnrageAsync(string bossId) => CallAsync("bossEnrage", bossId);
    public ValueTask BossDefeatedAsync(string bossId) => CallAsync("bossDefeated", bossId);
    public ValueTask BattleEndAsync() => CallAsync("battleEnd");

    // Sons (générés par le navigateur, sans fichier audio)
    public ValueTask PlayAsync(string sound) => CallAsync("play", sound);

    public async ValueTask<bool> ToggleSoundAsync() =>
        _module is not null && await _module.InvokeAsync<bool>("toggleSound");

    public async ValueTask<bool> IsSoundOnAsync() =>
        _module is not null && await _module.InvokeAsync<bool>("isSoundOn");

    private ValueTask CallAsync(string identifier, params object?[] args) =>
        _module is null ? ValueTask.CompletedTask : _module.InvokeVoidAsync(identifier, args);

    public async ValueTask DisposeAsync()
    {
        if (_module is null)
        {
            return;
        }

        try
        {
            await _module.InvokeVoidAsync("dispose");
            await _module.DisposeAsync();
        }
        catch (JSDisconnectedException)
        {
        }

        _module = null;
    }
}
