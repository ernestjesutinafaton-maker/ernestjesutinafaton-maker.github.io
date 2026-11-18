namespace ErnestWorld.Game;

public enum BattleStatus
{
    InProgress,
    Victory,
    Defeat,
}

/// <summary>Ce qui s'est passé après une réponse.</summary>
/// <param name="Correct">Bonne réponse ?</param>
/// <param name="Damage">Dégâts infligés au boss (0 si mauvaise réponse).</param>
/// <param name="Combo">Série de bonnes réponses d'affilée, celle-ci comprise.</param>
/// <param name="Critical">Coup critique (combo de 3 ou plus).</param>
/// <param name="HeartsLost">Cœurs perdus par le joueur.</param>
/// <param name="PhaseChanged">Le boss vient d'entrer en rage.</param>
/// <param name="Status">État du combat après ce tour.</param>
/// <param name="CorrectIndex">Position de la bonne réponse.</param>
/// <param name="Explanation">L'explication de la question.</param>
public sealed record TurnResult(
    bool Correct,
    int Damage,
    int Combo,
    bool Critical,
    int HeartsLost,
    bool PhaseChanged,
    BattleStatus Status,
    int CorrectIndex,
    Txt Explanation);

/// <summary>
/// Le moteur d'un combat de boss, au tour par tour :
/// une bonne réponse frappe le boss (plus fort en combo), une mauvaise coûte un cœur.
/// Il ne dépend ni de Blazor ni du navigateur : il est testé unitairement.
/// </summary>
public sealed class Battle
{
    /// <summary>Multiplicateur de dégâts selon la série en cours : 1×, puis 1,5×, puis 2× (critique).</summary>
    public static double ComboMultiplier(int combo) => combo switch
    {
        <= 1 => 1.0,
        2 => 1.5,
        _ => 2.0,
    };

    private readonly Random _random;
    private readonly Dictionary<int, Queue<Question>> _decks = [];

    public Battle(BossDefinition boss, int hearts, int hints, int seed)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(hearts, 1);
        ArgumentOutOfRangeException.ThrowIfNegative(hints);
        if (boss.Questions.Count == 0)
        {
            throw new ArgumentException("Un boss doit avoir au moins une question.", nameof(boss));
        }

        Boss = boss;
        BossHp = boss.MaxHp;
        MaxHearts = hearts;
        Hearts = hearts;
        Hints = hints;
        _random = new Random(seed);
        Phase = 1;
        Current = Draw();
        QuestionNumber = 1;
    }

    public BossDefinition Boss { get; }
    public int BossHp { get; private set; }
    public int MaxHearts { get; }
    public int Hearts { get; private set; }
    public int Hints { get; private set; }
    public int Combo { get; private set; }
    public int BestCombo { get; private set; }
    public int Phase { get; private set; }
    public int QuestionNumber { get; private set; }
    public BattleStatus Status { get; private set; } = BattleStatus.InProgress;
    public AskedQuestion Current { get; private set; }

    /// <summary>Victoire sans perdre un seul cœur.</summary>
    public bool IsFlawless => Status == BattleStatus.Victory && Hearts == MaxHearts;

    public double HpRatio => (double)BossHp / Boss.MaxHp;

    /// <summary>Répond à la question en cours.</summary>
    public TurnResult Answer(int choice)
    {
        EnsureInProgress();
        if (choice < 0 || choice >= Current.Choices.Count)
        {
            throw new ArgumentOutOfRangeException(nameof(choice));
        }

        var question = Current;
        var correct = choice == question.CorrectIndex;
        var damage = 0;
        var heartsLost = 0;
        var phaseChanged = false;

        if (correct)
        {
            Combo++;
            BestCombo = Math.Max(BestCombo, Combo);
            damage = (int)Math.Round(Boss.HitDamage * ComboMultiplier(Combo), MidpointRounding.AwayFromZero);
            BossHp = Math.Max(0, BossHp - damage);

            if (Boss.TwoPhases && Phase == 1 && BossHp > 0 && BossHp <= Boss.MaxHp / 2)
            {
                Phase = 2;
                phaseChanged = true;
            }

            if (BossHp == 0)
            {
                Status = BattleStatus.Victory;
            }
        }
        else
        {
            Combo = 0;
            heartsLost = 1;
            Hearts--;
            if (Hearts == 0)
            {
                Status = BattleStatus.Defeat;
            }
        }

        return new TurnResult(correct, damage, Combo, correct && Combo >= 3, heartsLost, phaseChanged,
            Status, question.CorrectIndex, question.Source.Explanation);
    }

    /// <summary>Passe à la question suivante (après avoir lu l'explication).</summary>
    public void Next()
    {
        EnsureInProgress();
        Current = Draw();
        QuestionNumber++;
    }

    /// <summary>Utilise un indice : retire deux mauvaises réponses. Renvoie les positions retirées.</summary>
    public IReadOnlyList<int> UseHint()
    {
        EnsureInProgress();
        if (Hints == 0)
        {
            return [];
        }

        var candidates = Enumerable.Range(0, Current.Choices.Count)
            .Where(i => i != Current.CorrectIndex && !Current.Removed.Contains(i))
            .OrderBy(_ => _random.Next())
            .Take(Math.Max(0, Math.Min(2, Current.Choices.Count - 2)))
            .ToList();

        if (candidates.Count == 0)
        {
            return [];
        }

        Hints--;
        candidates.ForEach(Current.Remove);
        return candidates;
    }

    private void EnsureInProgress()
    {
        if (Status != BattleStatus.InProgress)
        {
            throw new InvalidOperationException("Le combat est terminé.");
        }
    }

    /// <summary>
    /// Tire la prochaine question de la phase en cours, sans répétition tant que le paquet n'est pas
    /// épuisé. Si un boss n'a pas de question pour sa phase 2, il garde celles de la phase 1.
    /// </summary>
    private AskedQuestion Draw()
    {
        var phase = Boss.Questions.Any(q => q.Phase == Phase) ? Phase : 1;
        if (!_decks.TryGetValue(phase, out var deck) || deck.Count == 0)
        {
            var pool = Boss.Questions.Where(q => q.Phase == phase).OrderBy(_ => _random.Next()).ToList();
            deck = new Queue<Question>(pool);
            _decks[phase] = deck;
        }

        var question = deck.Dequeue();
        var choices = question.Wrong.Append(question.Answer).OrderBy(_ => _random.Next()).ToList();
        return new AskedQuestion(question, choices, choices.IndexOf(question.Answer));
    }
}
