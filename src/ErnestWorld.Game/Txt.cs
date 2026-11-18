namespace ErnestWorld.Game;

/// <summary>Les langues du site.</summary>
public enum Lang
{
    Fr,
    En,
}

/// <summary>
/// Un texte en français et en anglais. Une simple chaîne se convertit en <see cref="Txt"/>
/// identique dans les deux langues (pratique pour du code ou des nombres : « 6 », « false »…).
/// </summary>
public sealed record Txt(string Fr, string En)
{
    public string Get(Lang lang) => lang == Lang.En ? En : Fr;

    public static implicit operator Txt(string same) => new(same, same);

    public override string ToString() => Fr;
}
