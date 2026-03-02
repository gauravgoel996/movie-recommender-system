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
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFE11D48),
          secondary: Color(0xFFE11D48),
        ),
      ),
      home: const MainNavigationScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;
  List<String> _movieTitles = [];
  List<String> _userIds = [];
  bool _isLoadingData = true;

  @override
  void initState() {
    super.initState();
    _fetchDropdownData();
  }

  // Fetch the list of valid movies and users from the backend
  Future<void> _fetchDropdownData() async {
    try {
      final moviesRes = await http.get(
        Uri.parse('http://10.0.2.2:8000/movies'),
      );
      final usersRes = await http.get(Uri.parse('http://10.0.2.2:8000/users'));

      if (moviesRes.statusCode == 200 && usersRes.statusCode == 200) {
        setState(() {
          _movieTitles = List<String>.from(json.decode(moviesRes.body));
          // Convert User IDs to strings for the dropdown
          _userIds = List<dynamic>.from(
            json.decode(usersRes.body),
          ).map((e) => e.toString()).toList();
          _isLoadingData = false;
        });
      }
    } catch (e) {
      debugPrint("Error fetching dropdown data: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoadingData) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text("Connecting to Backend..."),
            ],
          ),
        ),
      );
    }

    // Our three different screens
    final tabs = [
      RecommendationView(type: 'content', optionsList: _movieTitles),
      RecommendationView(type: 'user', optionsList: _userIds),
      RecommendationView(type: 'hybrid', optionsList: _userIds),
    ];

    return Scaffold(
      body: tabs[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        backgroundColor: const Color(0xFF1E293B),
        selectedItemColor: const Color(0xFFE11D48),
        unselectedItemColor: Colors.grey,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.movie), label: 'Content'),
          BottomNavigationBarItem(
            icon: Icon(Icons.people),
            label: 'User-Based',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.merge_type),
            label: 'Hybrid',
          ),
        ],
      ),
    );
  }
}

class RecommendationView extends StatefulWidget {
  final String type;
  final List<String> optionsList;

  const RecommendationView({
    super.key,
    required this.type,
    required this.optionsList,
  });

  @override
  State<RecommendationView> createState() => _RecommendationViewState();
}

class _RecommendationViewState extends State<RecommendationView> {
  String? _selectedItem;
  List<dynamic> _recommendations = [];
  bool _isLoading = false;
  String _errorMessage = '';
  String _anchorMovie = '';

  Future<void> fetchRecommendations() async {
    if (_selectedItem == null || _selectedItem!.isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = '';
      _recommendations = [];
      _anchorMovie = '';
    });

    try {
      Uri url;
      if (widget.type == 'content') {
        url = Uri.parse(
          'http://10.0.2.2:8000/recommend/content?movie_title=${Uri.encodeComponent(_selectedItem!)}&num_recs=10',
        );
      } else if (widget.type == 'user') {
        url = Uri.parse(
          'http://10.0.2.2:8000/recommend/user?user_id=$_selectedItem&num_recs=10',
        );
      } else {
        url = Uri.parse(
          'http://10.0.2.2:8000/recommend/hybrid?user_id=$_selectedItem&num_recs=10',
        );
      }

      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _recommendations = data['recommendations'] ?? [];
          if (widget.type == 'hybrid' && data['anchor_movie'] != null) {
            _anchorMovie = data['anchor_movie'];
          }
        });
      } else {
        setState(() {
          _errorMessage =
              "No recommendations found. Please check your selection.";
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
    String title = widget.type == 'content'
        ? '🎥 Content-Based'
        : widget.type == 'user'
        ? '👥 User-Based'
        : '🧬 Hybrid';
    String hint = widget.type == 'content'
        ? 'Select or type a movie...'
        : 'Select a User ID...';

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Searchable Dropdown Row
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  // Autocomplete creates the searchable dropdown behavior
                  child: Autocomplete<String>(
                    optionsBuilder: (TextEditingValue textEditingValue) {
                      if (textEditingValue.text.isEmpty) {
                        return const Iterable<String>.empty();
                      }
                      return widget.optionsList.where((String option) {
                        return option.toLowerCase().contains(
                          textEditingValue.text.toLowerCase(),
                        );
                      });
                    },
                    onSelected: (String selection) {
                      _selectedItem = selection;
                      FocusScope.of(context).unfocus(); // Close keyboard
                    },
                    fieldViewBuilder:
                        (context, controller, focusNode, onEditingComplete) {
                          return TextField(
                            controller: controller,
                            focusNode: focusNode,
                            decoration: InputDecoration(
                              hintText: hint,
                              border: const OutlineInputBorder(),
                              filled: true,
                              fillColor: const Color(0xFF1E293B),
                              suffixIcon: const Icon(
                                Icons.arrow_drop_down,
                                color: Colors.white54,
                              ),
                            ),
                            onChanged: (val) => _selectedItem = val,
                          );
                        },
                    optionsViewBuilder: (context, onSelected, options) {
                      return Align(
                        alignment: Alignment.topLeft,
                        child: Material(
                          elevation: 4.0,
                          color: const Color(0xFF1E293B),
                          child: SizedBox(
                            height: 250.0,
                            // Set width to slightly less than screen width to account for margins
                            width: MediaQuery.of(context).size.width - 120,
                            child: ListView.builder(
                              padding: EdgeInsets.zero,
                              itemCount: options.length,
                              itemBuilder: (BuildContext context, int index) {
                                final String option = options.elementAt(index);
                                return ListTile(
                                  title: Text(
                                    option,
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                  onTap: () => onSelected(option),
                                );
                              },
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: () {
                    FocusScope.of(context).unfocus();
                    fetchRecommendations();
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFE11D48),
                    padding: const EdgeInsets.symmetric(
                      vertical: 20,
                      horizontal: 20,
                    ),
                  ),
                  child: const Text(
                    'Generate',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Hybrid Anchor Text
            if (_anchorMovie.isNotEmpty && widget.type == 'hybrid')
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(
                  'Because User $_selectedItem loved $_anchorMovie:',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 16,
                    fontStyle: FontStyle.italic,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),

            // Loading, Error, or Grid View
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.only(top: 50.0),
                child: CircularProgressIndicator(),
              )
            else if (_errorMessage.isNotEmpty)
              Text(
                _errorMessage,
                style: const TextStyle(color: Colors.redAccent),
              )
            else
              Expanded(
                child: GridView.builder(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 0.65,
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
                              // Add a small error builder in case image links break
                              errorBuilder: (context, error, stackTrace) =>
                                  Container(
                                    color: Colors.grey[800],
                                    child: const Icon(
                                      Icons.broken_image,
                                      size: 50,
                                      color: Colors.grey,
                                    ),
                                  ),
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
