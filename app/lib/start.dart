import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class StartScreen extends StatelessWidget {
  const StartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF163339), // bgColor from dashboard
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 40.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              // App Logo / Name
              const Center(
                child: Column(
                  children: [
                    Icon(
                      Icons.trending_up,
                      size: 100,
                      color: Color(0xFF5DF22A), // accentGreen
                    ),
                    SizedBox(height: 24),
                    Text(
                      'Stocki',
                      style: TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 2.0,
                      ),
                    ),
                    SizedBox(height: 16),
                    Text(
                      'Take control of your financial future.',
                      style: TextStyle(
                        fontSize: 16,
                        color: Color(0xFF8BA5A8), // textSecondary
                        fontWeight: FontWeight.w500,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              const Spacer(),
              // Get Started Button
              ElevatedButton(
                onPressed: () {
                  context.go('/signup');
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF5DF22A),
                  foregroundColor: const Color(0xFF163339),
                  padding: const EdgeInsets.symmetric(vertical: 18.0),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  'Get Started',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // Optional Alternative Action
              TextButton(
                onPressed: () {
                  context.go('/signup'); // Direct to same place for now
                },
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFF5DF22A),
                ),
                child: const Text(
                  'Already have an account? Log In',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
