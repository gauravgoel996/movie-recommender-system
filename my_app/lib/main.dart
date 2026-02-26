import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const MovieApp());
}

class MovieApp extends StatelessWidget {
  const MovieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Movie Recommender',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        primaryColor: const Color(0xFFE11D48),
      ),
      home: const MovieSearchScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MovieSearchScreen extends StatefulWidget {
  const MovieSearchScreen({super.key});

  @override
  // ignore: library_private_types_in_public_api
  _MovieSearchScreenState createState() => _MovieSearchScreenState();
}

class _MovieSearchScreenState extends State<MovieSearchScreen> {
  final TextEditingController _controller = TextEditingController();
  List<dynamic> _recommendations = [];
  bool _isLoading = false;
  String _errorMessage = '';

  Future<void> fetchMovies(String title) async {
    setState(() {
      _isLoading = true;
      _errorMessage = '';
    });

    try {
      // 10.0.2.2 points the Android emulator to your computer's local server
      final url = Uri.parse(
        'http://10.0.2.2:8000/recommend/content?movie_title=$title&num_recs=10',
      );
      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _recommendations = data['recommendations'];
        });
      } else {
        setState(() {
          _errorMessage =
              "Movie not found. Please try another title like 'Avatar'.";
          _recommendations = [];
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "Could not connect to the server. Is FastAPI running?";
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🎥 Movie Recommender'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Search Bar
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(
                      hintText: 'Enter a movie (e.g., Avatar)',
                      border: OutlineInputBorder(),
                      filled: true,
                      fillColor: Color(0xFF1E293B),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: () {
                    FocusScope.of(context).unfocus(); // Close keyboard
                    fetchMovies(_controller.text);
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFE11D48),
                    padding: const EdgeInsets.symmetric(
                      vertical: 20,
                      horizontal: 20,
                    ),
                  ),
                  child: const Text(
                    'Search',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Loading, Error, or Grid View
            if (_isLoading)
              const CircularProgressIndicator()
            else if (_errorMessage.isNotEmpty)
              Text(
                _errorMessage,
                style: const TextStyle(color: Colors.redAccent),
              )
            else
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2, // 2 posters per row on a phone
                    childAspectRatio: 0.65, // Poster aspect ratio
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                  ),
                  itemCount: _recommendations.length,
                  itemBuilder: (context, index) {
                    final movie = _recommendations[index];
                    return Column(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(8.0),
                            child: Image.network(
                              movie['poster_url'],
                              fit: BoxFit.cover,
                              width: double.infinity,
                            ),
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          movie['title'],
                          textAlign: TextAlign.center,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}
