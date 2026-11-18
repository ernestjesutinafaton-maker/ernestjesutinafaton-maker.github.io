namespace ErnestWorld.Game;

/// <summary>Un boss de la campagne.</summary>
/// <param name="Id">Identifiant, partagé avec le moteur 3D.</param>
/// <param name="Name">Nom affiché (« Le Golem du Réseau »).</param>
/// <param name="Title">Sous-titre (« Gardien du niveau 3 »).</param>
/// <param name="Lore">Petite histoire racontée avant le combat.</param>
/// <param name="Level">Niveau de la campagne qu'il garde (1 à 5).</param>
/// <param name="MaxHp">Points de vie.</param>
/// <param name="HitDamage">Dégâts d'une bonne réponse, avant les combos.</param>
/// <param name="XpReward">XP gagnés en le battant.</param>
/// <param name="AchievementId">Succès débloqué en le battant.</param>
/// <param name="Questions">Les questions qu'il pose.</param>
/// <param name="TwoPhases">S'il entre en rage à mi-vie (questions plus dures).</param>
/// <param name="AttackLine">Ce qu'il dit quand il frappe.</param>
/// <param name="DefeatLine">Ses derniers mots.</param>
public sealed record BossDefinition(
    string Id,
    Txt Name,
    Txt Title,
    Txt Lore,
    int Level,
    int MaxHp,
    int HitDamage,
    int XpReward,
    string AchievementId,
    IReadOnlyList<Question> Questions,
    bool TwoPhases,
    Txt AttackLine,
    Txt DefeatLine);
