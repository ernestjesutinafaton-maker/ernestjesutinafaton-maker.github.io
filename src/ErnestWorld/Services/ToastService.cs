namespace ErnestWorld.Services;

/// <summary>Une notification façon jeu vidéo (« Lieu découvert », « Succès débloqué »…).</summary>
/// <param name="Kind">Type de notification, qui choisit le son joué (discover, achievement, levelup…).</param>
public sealed record Toast(Guid Id, string Title, string Text, string Icon, string? Kind);

/// <summary>Diffuse les notifications au composant <c>Toasts</c>.</summary>
public sealed class ToastService
{
    public event Action<Toast>? Shown;

    public void Show(string title, string text, string icon = "spark", string? kind = null) =>
        Shown?.Invoke(new Toast(Guid.NewGuid(), title, text, icon, kind));
}
