using System.Net.Mail;
using Microsoft.Extensions.Configuration;

namespace ErnestWorld.Services;

/// <summary>Comment les inscriptions sont transmises.</summary>
public enum NewsletterMode
{
    /// <summary>Le visiteur envoie un email pré-rempli à Ernest (fonctionne sans aucun service).</summary>
    Mailto,

    /// <summary>Le formulaire est envoyé à Buttondown, qui gère la liste et l'email de confirmation.</summary>
    Buttondown,
}

/// <summary>
/// La newsletter. Le mode se règle dans wwwroot/appsettings.json, section « Newsletter ».
/// </summary>
public sealed class NewsletterService
{
    public NewsletterService(IConfiguration configuration)
    {
        var section = configuration.GetSection("Newsletter");
        ContactEmail = section["ContactEmail"] ?? "ernestjesutinafaton@gmail.com";
        ButtondownUsername = section["ButtondownUsername"]?.Trim() ?? string.Empty;
        Mode = string.Equals(section["Provider"], "buttondown", StringComparison.OrdinalIgnoreCase)
               && ButtondownUsername.Length > 0
            ? NewsletterMode.Buttondown
            : NewsletterMode.Mailto;
    }

    public NewsletterMode Mode { get; }
    public string ContactEmail { get; }
    public string ButtondownUsername { get; }

    /// <summary>Adresse à laquelle le formulaire Buttondown est envoyé.</summary>
    public string ButtondownAction => $"https://buttondown.com/api/emails/embed-subscribe/{Uri.EscapeDataString(ButtondownUsername)}";

    /// <summary>Vérifie qu'une adresse email a une forme valide.</summary>
    public static bool IsValidEmail(string? email)
    {
        if (string.IsNullOrWhiteSpace(email) || email.Length > 254)
        {
            return false;
        }

        return MailAddress.TryCreate(email.Trim(), out var address)
               && address.Address == email.Trim()
               && address.Host.Contains('.');
    }

    /// <summary>Lien « mailto » pré-rempli pour le mode sans service.</summary>
    public string MailtoLink(string visitorEmail)
    {
        var subject = Uri.EscapeDataString("Inscription à la newsletter");
        var body = Uri.EscapeDataString(
            $"Bonjour Ernest,\n\nJe souhaite recevoir ta newsletter à cette adresse : {visitorEmail.Trim()}\n\nÀ bientôt !");
        return $"mailto:{ContactEmail}?subject={subject}&body={body}";
    }
}
