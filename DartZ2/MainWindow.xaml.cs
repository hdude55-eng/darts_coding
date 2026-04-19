using System.Collections.ObjectModel;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace DartScorer
{
    public partial class MainWindow : Window
    {
        public ObservableCollection<GameTurn> Turns= new();
        public ObservableCollection<GameTurn> Players = new();

        int currentValue = 0;
        int currentMultiplier = 1;

        public MainWindow()
        {
            InitializeComponent();

               PlayerSelector.Items.Add("Ben");
               PlayerSelector.Items.Add("JD");
               PlayerSelector.Items.Add("Harry");
               PlayerSelector.Items.Add("Champ");
               PlayerSelector.SelectedIndex = 0;
               currentValue = 0;
               CurrentValue.Text = currentValue.ToString();
               ScoreGrid.ItemsSource = Turns;

               Players.Add(new GameTurn { PlayerName = "Ben", Remaining = 501, GameNumber = 1 });
               Players.Add(new GameTurn { PlayerName = "JD", Remaining = 501, GameNumber = 1 });
               Players.Add(new GameTurn { PlayerName = "Harry", Remaining = 501, GameNumber = 1 });
               Players.Add(new GameTurn { PlayerName = "Champ", Remaining = 501, GameNumber = 1 });

            ScoreGrid.ItemsSource = Players;
            HistoryGrid.ItemsSource = Turns;
        }

        private void Export_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "CSV file (*.csv)|*.csv",
                FileName = "DartGame.csv"
            };

            if (dialog.ShowDialog() == true)
            {
                using (var writer = new System.IO.StreamWriter(dialog.FileName))
                {
                    // Header
                    writer.WriteLine("Player,Turn,D1,D2,D3,Total,Remaining");

                    foreach (var t in Turns)
                    {
                        writer.WriteLine($"{t.PlayerName},{t.GameNumber},{t.Dart1},{t.Dart2},{t.Dart3},{t.Total},{t.Remaining}");
                    }
                }

                MessageBox.Show("Export completed!");
            }
        }

        private void NewGame_Click(object sender, RoutedEventArgs e)
        {
            foreach (var p in Players)
            {
                p.GameNumber = 1;
                p.Remaining = 501;

                p.Dart1 = p.Dart2 = p.Dart3 = null;
                p.Score1 = p.Score2 = p.Score3 = 0;

                p.PrevDart1 = p.PrevDart2 = p.PrevDart3 = null;
                p.PrevScore1 = p.PrevScore2 = p.PrevScore3 = 0;
                p.PrevGameNumber = 0;
            }

            Turns.Clear();

            ScoreGrid.Items.Refresh();
            HistoryGrid.Items.Refresh();

            ResetInputState();
        }

        private void Score_Click(object sender, RoutedEventArgs e)
        {
            Button btn = sender as Button;
            string content = btn.Content.ToString();

            if (content.Contains("Bull"))
            {
                currentValue = 25; // or 50 if you prefer full bull only

                HandleBullSelection();
            }
            else
            {
                currentValue = int.Parse(content);

                HandleNormalNumberSelection();
            }

            UpdateCurrentValueDisplay();
        }

        private void HandleBullSelection()
        {
            // Disable Triple
            TripleBtn.IsEnabled = false;

            // If Triple was selected → revert to Single
            if (TripleBtn.IsChecked == true)
            {
                SingleBtn.IsChecked = true;
            }
        }

        private void HandleNormalNumberSelection()
        {
            // Re-enable Triple when not Bull
            TripleBtn.IsEnabled = true;
        }

        private void Enter_Click(object sender, RoutedEventArgs e)
        {
            if (currentValue == 0) return;

            string player = PlayerSelector.SelectedItem.ToString();
            var game = Players.First(p => p.PlayerName == player);

            // Multiplier
            if (DoubleBtn.IsChecked == true) currentMultiplier = 2;
            else if (TripleBtn.IsChecked == true) currentMultiplier = 3;
            else currentMultiplier = 1;

            string dartText = $"{currentValue} {(currentMultiplier == 1 ? "S" : currentMultiplier == 2 ? "D" : "T")}";
            int score = currentValue * currentMultiplier;

            int newRemaining = game.Remaining - score;

            // 🎯 RULES HERE
            if (newRemaining < 0 ||
                newRemaining == 1 ||
                (newRemaining == 0 && currentMultiplier != 2))
            {
                MessageBox.Show("Bust!");

                game.CompleteTurn();   // lose turn
                ScoreGrid.Items.Refresh();
                return;
            }


            // ✅ FIRST assign dart
            if (Dart1Btn.IsChecked == true)
                game.SetDart(1, dartText, score);
            else if (Dart2Btn.IsChecked == true)
                game.SetDart(2, dartText, score);
            else if (Dart3Btn.IsChecked == true)
                game.SetDart(3, dartText, score);

            // ✅ THEN check if complete
            if (game.IsComplete)
            {
                // 👉 FIRST: copy current → previous (for the grid)
                game.PrevGameNumber = game.GameNumber;

                game.PrevDart1 = game.Dart1;
                game.PrevDart2 = game.Dart2;
                game.PrevDart3 = game.Dart3;

                game.PrevScore1 = game.Score1;
                game.PrevScore2 = game.Score2;
                game.PrevScore3 = game.Score3;

                // 👉 SECOND: save to history
                Turns.Add(new GameTurn
                {
                    PlayerName = game.PlayerName,
                    GameNumber = game.GameNumber,
                    Dart1 = game.Dart1,
                    Dart2 = game.Dart2,
                    Dart3 = game.Dart3,
                    Score1 = game.Score1,
                    Score2 = game.Score2,
                    Score3 = game.Score3,
                    Remaining = game.Remaining
                });

                // 👉 THIRD: reset for next turn
                game.CompleteTurn();
            }

            ScoreGrid.Items.Refresh();

            // Reset for next dart
            SingleBtn.IsChecked = true;
            DartNext();
        }

        private int GetNextGameNumber(string player)
        {
            int count = 0;
            foreach (var t in Players)   // Players was Turns
            {
                if (t.PlayerName == player)
                    count++;
            }
            return count + 1;
        }

        private void Miss_Click(object sender, RoutedEventArgs e)
        {
            currentValue = 0;
            currentMultiplier = 1;

            string player = PlayerSelector.SelectedItem.ToString();
            var game = Players.First(p => p.PlayerName == player);

            if (Dart1Btn.IsChecked == true)
                game.SetDart(1, "MISS", 0);
            else if (Dart2Btn.IsChecked == true)
                game.SetDart(2, "MISS", 0);
            else if (Dart3Btn.IsChecked == true)
                game.SetDart(3, "MISS", 0);

            // Check completion
            if (game.IsComplete)
                CompleteTurnFlow(game);

            ScoreGrid.Items.Refresh();
            DartNext();
        }

        private void CompleteTurnFlow(GameTurn game)
        {
            // Copy to previous
            game.PrevGameNumber = game.GameNumber;
            game.PrevDart1 = game.Dart1;
            game.PrevDart2 = game.Dart2;
            game.PrevDart3 = game.Dart3;

            game.PrevScore1 = game.Score1;
            game.PrevScore2 = game.Score2;
            game.PrevScore3 = game.Score3;

            // Save to history
            Turns.Add(new GameTurn
            {
                PlayerName = game.PlayerName,
                GameNumber = game.GameNumber,
                Dart1 = game.Dart1,
                Dart2 = game.Dart2,
                Dart3 = game.Dart3,
                Score1 = game.Score1,
                Score2 = game.Score2,
                Score3 = game.Score3,
                Remaining = game.Remaining
            });
            
            // Reset
            game.CompleteTurn();
        }

        private void DartNext()
        {
            if (Dart1Btn.IsChecked == true)
                Dart2Btn.IsChecked = true;
            else if (Dart2Btn.IsChecked == true)
                Dart3Btn.IsChecked = true;
            else
                Dart1Btn.IsChecked = true;
        }

        private void Multiplier_Changed(object sender, RoutedEventArgs e)
        {
            UpdateCurrentValueDisplay();
        }
        private void UpdateCurrentValueDisplay()
        {
            if (currentValue == 0)
            {
                CurrentValue.Text = "";
                return;
            }

            int multiplier = 1;

            if (DoubleBtn.IsChecked == true) multiplier = 2;
            else if (TripleBtn.IsChecked == true) multiplier = 3;

            int result = currentValue * multiplier;

            CurrentValue.Text = result.ToString();
        }

        private string lastPlayer = null;

        private void PlayerSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            string currentPlayer = PlayerSelector.SelectedItem.ToString();

            if (lastPlayer != null && lastPlayer != currentPlayer)
            {
                // lastPlayer can be stale after renaming in SetPlayers (no longer in Players)
                var previousPlayer = Players.FirstOrDefault(p => p.PlayerName == lastPlayer);
                if (previousPlayer != null && previousPlayer.Total > 0)
                {
                    ShiftToPrevious(previousPlayer);
                }
            }

            lastPlayer = currentPlayer;

            ResetInputState();
            ScoreGrid.Items.Refresh();
        }
        private void ResetInputState()
        {
            // Reset multiplier
            SingleBtn.IsChecked = true;

            // Reset dart selection
            Dart1Btn.IsChecked = true;

            // Clear current value display
            currentValue = 0;
            CurrentValue.Text = "  ";
        }

        private void ShiftToPrevious(GameTurn player)
        {
            // Move current values to previous
            player.PrevGameNumber = player.GameNumber;

            player.PrevDart1 = player.Dart1;
            player.PrevDart2 = player.Dart2;
            player.PrevDart3 = player.Dart3;

            player.PrevScore1 = player.Score1;
            player.PrevScore2 = player.Score2;
            player.PrevScore3 = player.Score3;

            // Reset current turn
            player.Dart1 = null;
            player.Dart2 = null;
            player.Dart3 = null;

            player.Score1 = 0;
            player.Score2 = 0;
            player.Score3 = 0;

            player.GameNumber++;
        }

        private void SetPlayers_Click(object sender, RoutedEventArgs e)
        {
            // disable PlayerSelector Changed
            PlayerSelector.SelectionChanged -= PlayerSelector_SelectionChanged;

            for (int i = 0; i < Players.Count; i++)
            {
                string name = Microsoft.VisualBasic.Interaction.InputBox(
                    $"Enter name for Player {i + 1}",
                    "Player Name",
                    Players[i].PlayerName);
          //      if (DialogResult == true)   //OK cliked
                {
                    if (!string.IsNullOrWhiteSpace(name))
                        Players[i].PlayerName = name;
                    //     int index = [i]
                    PlayerSelector.Items[i] = name;
                }
            }

            ScoreGrid.Items.Refresh();
            PlayerSelector.Items.Refresh();
            // Keep in sync with renamed players (lastPlayer used to resolve "previous" on switch)
            lastPlayer = PlayerSelector.SelectedItem?.ToString();
            // enable PlayerSelector Changed
            PlayerSelector.SelectionChanged += PlayerSelector_SelectionChanged;
        }

    }

   
    public class GameTurn
    {


        public string PlayerName { get; set; }
        public int GameNumber { get; set; }

        public string Dart1 { get; set; }
        public string Dart2 { get; set; }
        public string Dart3 { get; set; }

        public int Score1 { get; set; }
        public int Score2 { get; set; }
        public int Score3 { get; set; }

        public int Total => Score1 + Score2 + Score3;

        public int Remaining { get; set; }

        public int PrevGameNumber { get; set; }

        public string PrevDart1 { get; set; }
        public string PrevDart2 { get; set; }
        public string PrevDart3 { get; set; }

        public int PrevScore1 { get; set; }
        public int PrevScore2 { get; set; }
        public int PrevScore3 { get; set; }

        public int PrevTotal => PrevScore1 + PrevScore2 + PrevScore3;
        public bool IsComplete => Dart1 != null && Dart2 != null && Dart3 != null;

        public void CompleteTurn()
        {
            // Move to next turn
            GameNumber++;

            // Reset dart values
            Dart1 = null;
            Dart2 = null;
            Dart3 = null;

            Score1 = 0;
            Score2 = 0;
            Score3 = 0;
        }

        public void SetDart(int dart, string text, int score)
        {
            if (dart == 1)
            {
                Remaining += Score1;
                Dart1 = text;
                Score1 = score;
            }
            else if (dart == 2)
            {
                Remaining += Score2;
                Dart2 = text;
                Score2 = score;
            }
            else if (dart == 3)
            {
                Remaining += Score3;
                Dart3 = text;
                Score3 = score;
            }

            Remaining -= score;
        }
    }
}