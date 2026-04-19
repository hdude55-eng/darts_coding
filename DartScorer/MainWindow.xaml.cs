using System.Windows;
using System.Windows.Controls;

namespace DartScorer
{
    public partial class MainWindow : Window
    {
        int score = 501;

        public MainWindow()
        {
            InitializeComponent();
        }

        private void Score_Click(object sender, RoutedEventArgs e)
        {
            Button btn = sender as Button;
            int value = 0;

            if (btn.Content.ToString().Contains("Bull"))
                value = 50;
            else if (btn.Content.ToString() == "Miss")
                value = 0;
            else
                value = int.Parse(btn.Content.ToString());

            score -= value;

            if (score < 0)
            {
                MessageBox.Show("Bust!");
                score += value;
            }

            ScoreText.Text = score.ToString();
        }
    }
}