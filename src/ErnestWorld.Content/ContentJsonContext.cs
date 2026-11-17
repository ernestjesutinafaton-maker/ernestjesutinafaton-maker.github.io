using System.Text.Json.Serialization;

namespace ErnestWorld.Content;

/// <summary>
/// Sérialisation JSON générée à la compilation (plus rapide et compatible avec le
/// « trimming » de Blazor WebAssembly, qui supprime le code inutilisé).
/// </summary>
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    WriteIndented = true)]
[JsonSerializable(typeof(List<PostMeta>))]
public partial class ContentJsonContext : JsonSerializerContext;
