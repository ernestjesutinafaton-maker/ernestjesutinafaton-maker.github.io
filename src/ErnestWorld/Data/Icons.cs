namespace ErnestWorld.Data;

/// <summary>Icônes au trait (chemins SVG 24×24), partagées par l'interface et les étiquettes 3D.</summary>
public static class Icons
{
    private static readonly Dictionary<string, string> All = new()
    {
        // Lieux
        ["chateau"] = "M4 21V9h2V6h2v3h2V6h4v3h2V6h2v3h2v12zM10 21v-4a2 2 0 0 1 4 0v4",
        ["forge"] = "M14 4l6 6-3 3-6-6zM11 7L4 14l3 3 7-7M3 21h8",
        ["qg"] = "M4 21V5h10v16M14 9h6v12M7 9h4M7 13h4M7 17h4M3 21h18",
        ["academie"] = "M2 9l10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5M22 9v6",
        ["camp"] = "M3 21L12 4l9 17zM12 4v17M9 21l3-6 3 6",
        ["banque"] = "M3 10l9-6 9 6M5 10v8M9 10v8M15 10v8M19 10v8M3 21h18",
        ["marche"] = "M3 9l2-5h14l2 5M3 9h18v2a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0zM5 13v8h14v-8",
        ["observatoire"] = "M12 3a7 7 0 0 1 7 7H5a7 7 0 0 1 7-7zM6 10v11h12V10M10 21v-5h4v5",
        ["arene"] = "M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18M12 7a5 5 0 1 0 0 10 5 5 0 1 0 0-10M12 11a1 1 0 1 0 0 2 1 1 0 1 0 0-2",
        ["bibliotheque"] = "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 21a2 2 0 0 1 2-2h13v2",
        ["ruche"] = "M12 2l8.66 5v10L12 22l-8.66-5V7z",
        ["radio"] = "M12 10v11M8 21h8M7.8 5.8a6 6 0 0 0 0 8.4M16.2 5.8a6 6 0 0 1 0 8.4M5 3a10 10 0 0 0 0 14M19 3a10 10 0 0 1 0 14",
        ["scriptorium"] = "M20 3c-7 1-11 6-12 13l-3 5M8 16c4-1 8-4 9-9M20 3c0 5-2 10-7 12",
        ["pigeonnier"] = "M22 2L11 13M22 2l-7 20-4-9-9-4z",
        ["monument"] = "M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a3 3 0 0 0 3 3M17 6h3a3 3 0 0 1-3 3",
        ["phare"] = "M9 21l1-12h4l1 12zM8 21h8M10 9V6h4v3M12 6V3M4 6l4 1M20 6l-4 1",

        // Interface
        ["moon"] = "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
        ["sun"] = "M12 8a4 4 0 1 0 0 8 4 4 0 1 0 0-8M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
        ["home"] = "M3 12l9-9 9 9M5 10v10h14V10",
        ["play"] = "M7 4v16l13-8z",
        ["stop"] = "M6 6h12v12H6z",
        ["trophy"] = "M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a3 3 0 0 0 3 3M17 6h3a3 3 0 0 1-3 3",
        ["book"] = "M2 5h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2zM22 5h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z",
        ["page"] = "M4 3h16v18H4zM8 8h8M8 12h8M8 16h5",
        ["close"] = "M6 6l12 12M18 6L6 18",
        ["map"] = "M9 4L3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14",
        ["crown"] = "M3 8l4 4 5-7 5 7 4-4-2 11H5zM5 21h14",
        ["rss"] = "M5 19a1 1 0 1 0 0 .01M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16",
        ["arrow-left"] = "M19 12H5M11 6l-6 6 6 6",
        ["check"] = "M5 12l5 5 9-10",
        ["lock"] = "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
        ["spark"] = "M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z",

        // Combat
        ["skull"] = "M12 3a8 8 0 0 0-8 8c0 3 1.6 5.2 4 6.3V21h8v-3.7c2.4-1.1 4-3.3 4-6.3a8 8 0 0 0-8-8zM9 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 1 0 0-3M15 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 1 0 0-3M10 18v3M14 18v3",
        ["sword"] = "M14.5 17.5L3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2",
        ["heart"] = "M12 21s-7-4.5-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.5-9.5 9-9.5 9z",
        ["shield"] = "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z",
        ["bolt"] = "M13 2L4 14h7l-1 8 9-12h-7z",
        ["volume"] = "M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12",
        ["mute"] = "M4 9h4l5-4v14l-5-4H4zM17 9l4 6M21 9l-4 6",
        ["bug"] = "M8 9a4 4 0 0 1 8 0v7a4 4 0 0 1-8 0zM12 9v11M4 11h4M16 11h4M4 17h4M16 17h4M9 4l1.5 2M15 4l-1.5 2",
        ["wave"] = "M2 7c2-2 4-2 6 0s4 2 6 0 4-2 6 0M2 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0M2 17c2-2 4-2 6 0s4 2 6 0 4-2 6 0",
        ["cube"] = "M12 2l9 5v10l-9 5-9-5V7zM12 12l9-5M12 12L3 7M12 12v10",
        ["anchor"] = "M12 4a2 2 0 1 0 0 4 2 2 0 1 0 0-4M12 8v13M5 13H3a9 9 0 0 0 18 0h-2M8 11h8",
        ["flame"] = "M12 22c4 0 7-3 7-7 0-5-5-7-5-12-3 2-4 5-4 7-1-1-2-2-2-4-2 2-3 5-3 7 0 5 3 9 7 9z",
        ["flag"] = "M5 21V4M5 4h11l-2 4 2 4H5",
    };

    public static string Path(string id) => All.TryGetValue(id, out var path) ? path : All["spark"];
}
