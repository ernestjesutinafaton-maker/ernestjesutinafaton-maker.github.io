namespace ErnestWorld.Services;

/// <summary>Une notification façon jeu vidéo (« Lieu découvert », « Succès débloqué »…).</summary>
public sealed record Toast(Guid Id, string Title, string Text, string Icon);

/// <summary>Diffuse les notifications au composant <c>Toasts</c>.</summary>
public sealed class ToastService
{
    public event Action<Toast>? Shown;

    public void Show(string title, string text, string icon = "spark") =>
        Shown?.Invoke(new Toast(Guid.NewGuid(), title, text, icon));
}
