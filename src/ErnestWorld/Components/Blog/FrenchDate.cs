namespace ErnestWorld.Components.Blog;

/// <summary>
/// Dates en français, sans dépendre des données de culture du navigateur
/// (Blazor WebAssembly ne les charge pas toutes).
/// </summary>
public static class FrenchDate
{
    private static readonly string[] Months =
    [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ];

    public static string Format(DateOnly date) => $"{date.Day} {Months[date.Month - 1]} {date.Year}";
}
