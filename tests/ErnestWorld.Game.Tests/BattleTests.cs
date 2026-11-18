using ErnestWorld.Game;

namespace ErnestWorld.Game.Tests;

public class BattleTests
{
    private static BossDefinition TestBoss(int hp = 90, bool twoPhases = false, int questions = 4) => new(
        Id: "test", Name: "Boss de test", Title: "", Lore: "", Level: 1, MaxHp: hp, HitDamage: 30, XpReward: 100,
        AchievementId: "test", TwoPhases: twoPhases, AttackLine: "", DefeatLine: "",
        Questions:
        [
            .. Enumerable.Range(1, questions).Select(i => new Question($"Q{i}", $"bon{i}", [$"faux{i}a", $"faux{i}b", $"faux{i}c"], "")),
            .. twoPhases ? [new Question("Q-rage", "bon-rage", ["x", "y", "z"], "", Phase: 2)] : Array.Empty<Question>(),
        ]);

    private static int Wrong(Battle battle) => (battle.Current.CorrectIndex + 1) % battle.Current.Choices.Count;

    [Fact]
    public void Une_bonne_reponse_frappe_le_boss()
    {
        var battle = new Battle(TestBoss(), hearts: 3, hints: 0, seed: 1);

        var result = battle.Answer(battle.Current.CorrectIndex);

        Assert.True(result.Correct);
        Assert.Equal(30, result.Damage);
        Assert.Equal(60, battle.BossHp);
        Assert.Equal(3, battle.Hearts);
    }

    [Fact]
    public void Les_combos_augmentent_les_degats_et_le_troisieme_est_critique()
    {
        var battle = new Battle(TestBoss(hp: 500), hearts: 3, hints: 0, seed: 2);

        var first = battle.Answer(battle.Current.CorrectIndex); battle.Next();
        var second = battle.Answer(battle.Current.CorrectIndex); battle.Next();
        var third = battle.Answer(battle.Current.CorrectIndex);

        Assert.Equal([30, 45, 60], new[] { first.Damage, second.Damage, third.Damage });
        Assert.False(second.Critical);
        Assert.True(third.Critical);
        Assert.Equal(3, battle.BestCombo);
    }

    [Fact]
    public void Une_mauvaise_reponse_coute_un_coeur_et_casse_le_combo()
    {
        var battle = new Battle(TestBoss(hp: 500), hearts: 3, hints: 0, seed: 3);
        battle.Answer(battle.Current.CorrectIndex);
        battle.Next();

        var result = battle.Answer(Wrong(battle));

        Assert.False(result.Correct);
        Assert.Equal(1, result.HeartsLost);
        Assert.Equal(2, battle.Hearts);
        Assert.Equal(0, battle.Combo);
    }

    [Fact]
    public void Plus_de_coeurs_signifie_la_defaite()
    {
        var battle = new Battle(TestBoss(), hearts: 1, hints: 0, seed: 4);

        var result = battle.Answer(Wrong(battle));

        Assert.Equal(BattleStatus.Defeat, result.Status);
        Assert.Throws<InvalidOperationException>(() => battle.Next());
    }

    [Fact]
    public void Le_boss_tombe_a_zero_PV_et_la_victoire_sans_degat_est_parfaite()
    {
        var battle = new Battle(TestBoss(hp: 90), hearts: 3, hints: 0, seed: 5);

        battle.Answer(battle.Current.CorrectIndex); battle.Next();      // 30
        var last = battle.Answer(battle.Current.CorrectIndex);           // 45 → 15 PV restants ?
        if (last.Status != BattleStatus.Victory)
        {
            battle.Next();
            last = battle.Answer(battle.Current.CorrectIndex);
        }

        Assert.Equal(BattleStatus.Victory, last.Status);
        Assert.Equal(0, battle.BossHp);
        Assert.True(battle.IsFlawless);
    }

    [Fact]
    public void Le_boss_final_entre_en_rage_a_mi_vie_et_change_de_questions()
    {
        var battle = new Battle(TestBoss(hp: 120, twoPhases: true), hearts: 5, hints: 0, seed: 6);

        var first = battle.Answer(battle.Current.CorrectIndex); battle.Next();   // 30 → 90 PV
        var second = battle.Answer(battle.Current.CorrectIndex);                // 45 → 45 PV : rage

        Assert.False(first.PhaseChanged);
        Assert.True(second.PhaseChanged);
        Assert.Equal(2, battle.Phase);
        battle.Next();
        Assert.Equal("Q-rage", battle.Current.Source.Prompt.Fr);
    }

    [Fact]
    public void Un_indice_retire_deux_mauvaises_reponses_jamais_la_bonne()
    {
        var battle = new Battle(TestBoss(), hearts: 3, hints: 1, seed: 7);

        var removed = battle.UseHint();

        Assert.Equal(2, removed.Count);
        Assert.DoesNotContain(battle.Current.CorrectIndex, removed);
        Assert.Equal(0, battle.Hints);
        Assert.Empty(battle.UseHint());
    }

    [Fact]
    public void Les_questions_ne_se_repetent_pas_avant_d_avoir_toutes_ete_posees()
    {
        var battle = new Battle(TestBoss(hp: 10_000, questions: 4), hearts: 99, hints: 0, seed: 8);
        var seen = new List<string>();

        for (var i = 0; i < 4; i++)
        {
            seen.Add(battle.Current.Source.Prompt.Fr);
            battle.Answer(battle.Current.CorrectIndex);
            battle.Next();
        }

        Assert.Equal(4, seen.Distinct().Count());
    }

    [Fact]
    public void La_bonne_reponse_est_bien_placee_apres_melange()
    {
        var battle = new Battle(TestBoss(), hearts: 3, hints: 0, seed: 9);

        Assert.Equal(battle.Current.Source.Answer, battle.Current.Choices[battle.Current.CorrectIndex]);
        Assert.Equal(4, battle.Current.Choices.Count);
    }
}

public class BestiaryTests
{
    public static TheoryData<string> BossIds => [.. Bestiary.All.Select(b => b.Id)];

    [Theory]
    [MemberData(nameof(BossIds))]
    public void Chaque_question_est_bien_formee(string id)
    {
        var boss = Bestiary.Find(id)!;

        foreach (var q in boss.Questions)
        {
            Assert.Equal(3, q.Wrong.Count);
            Assert.DoesNotContain(q.Answer, q.Wrong);
            Assert.Equal(q.Wrong.Count, q.Wrong.Distinct().Count());

            // Chaque texte existe dans les deux langues, et les choix restent distincts en anglais aussi
            foreach (var text in new[] { q.Prompt, q.Answer, q.Explanation }.Concat(q.Wrong))
            {
                Assert.False(string.IsNullOrWhiteSpace(text.Fr), $"{boss.Id} : texte français manquant");
                Assert.False(string.IsNullOrWhiteSpace(text.En), $"{boss.Id} : texte anglais manquant ({text.Fr})");
            }

            Assert.Equal(4, q.Wrong.Append(q.Answer).Select(t => t.En).Distinct().Count());
        }
    }

    [Theory]
    [MemberData(nameof(BossIds))]
    public void Chaque_boss_est_traduit(string id)
    {
        var boss = Bestiary.Find(id)!;

        foreach (var text in new[] { boss.Name, boss.Title, boss.Lore, boss.AttackLine, boss.DefeatLine })
        {
            Assert.False(string.IsNullOrWhiteSpace(text.En));
            Assert.NotEqual(text.Fr, text.En);
        }
    }

    [Theory]
    [MemberData(nameof(BossIds))]
    public void Chaque_boss_a_assez_de_questions_pour_etre_battu_sans_repetition(string id)
    {
        var boss = Bestiary.Find(id)!;
        var hitsNeeded = (int)Math.Ceiling(boss.MaxHp / (double)boss.HitDamage);

        Assert.True(boss.Questions.Count >= hitsNeeded, $"{boss.Name} : {boss.Questions.Count} questions pour {hitsNeeded} coups.");
    }

    [Fact]
    public void Le_boss_final_a_des_questions_de_rage_et_les_niveaux_se_suivent()
    {
        Assert.Contains(Bestiary.Dragon.Questions, q => q.Phase == 2);
        Assert.Equal([1, 2, 3, 4, 5], Bestiary.All.Select(b => b.Level));
        Assert.Equal(Bestiary.All.Count, Bestiary.All.Select(b => b.Id).Distinct().Count());
    }
}
