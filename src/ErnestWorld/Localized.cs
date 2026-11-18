using ErnestWorld.Game;
using Microsoft.AspNetCore.Components;

namespace ErnestWorld;

/// <summary>
/// Base de tous les composants du site (voir _Imports.razor) : donne la langue en cours
/// et les raccourcis de traduction. Quand la langue change, MainLayout la diffuse
/// (CascadingValue) et chaque composant se redessine dans la nouvelle langue.
/// </summary>
public abstract class Localized : ComponentBase
{
    [CascadingParameter(Name = "lang")]
    public Lang Language { get; set; }

    protected bool En => Language == Lang.En;

    /// <summary>Choisit le texte français ou anglais.</summary>
    protected string T(string fr, string en) => En ? en : fr;

    /// <summary>Lit un texte bilingue dans la langue en cours.</summary>
    protected string T(Txt text) => text.Get(Language);
}
