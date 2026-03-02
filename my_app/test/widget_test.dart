import 'package:flutter_test/flutter_test.dart';
import 'package:my_app/main.dart';

void main() {
  testWidgets('Movie Recommender UI smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame using your actual main class.
    await tester.pumpWidget(const MovieApp());

    // Verify that the App Bar title exists.
    expect(find.text('🎥 Movie Recommender'), findsOneWidget);

    // Verify that the Search button exists.
    expect(find.text('Search'), findsOneWidget);

    // Verify that the text field hint is present.
    expect(find.text('Enter a movie (e.g., Avatar)'), findsOneWidget);
  });
}
