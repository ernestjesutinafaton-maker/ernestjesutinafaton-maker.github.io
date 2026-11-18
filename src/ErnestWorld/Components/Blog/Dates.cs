using ErnestWorld.Game;

namespace ErnestWorld.Components.Blog;

/// <summary>
/// Dates en français ou en anglais, sans dépendre des données de culture du navigateur
/// (Blazor WebAssembly ne les charge pas toutes).
/// </summary>
public static class Dates
{
    private static readonly string[] French =
    [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ];

    private static readonly string[] English =
    [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];

    /// <summary>« 12 mars 2026 » ou « March 12, 2026 ».</summary>
    public static string Format(DateOnly date, Lang lang) => lang == Lang.En
        ? $"{English[date.Month - 1]} {date.Day}, {date.Year}"
        : $"{date.Day} {French[date.Month - 1]} {date.Year}";
}
