import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class BankAccScreen extends StatelessWidget {
  const BankAccScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF163339),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          'Connect Accounts',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () {
            context.go('/signup');
          },
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Link Your Financials',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Connect your bank accounts and credit cards to get a unified view of your finances.',
                style: TextStyle(
                  fontSize: 16,
                  color: Color(0xFF8BA5A8),
                ),
              ),
              const SizedBox(height: 40),

              _buildConnectionCard(
                context,
                icon: Icons.account_balance,
                title: 'Link Bank Account',
                subtitle: 'Checking, Savings, Investments',
                color: Colors.blueAccent,
              ),
              const SizedBox(height: 16),
              _buildConnectionCard(
                context,
                icon: Icons.credit_card,
                title: 'Add Credit Card',
                subtitle: 'Visa, Mastercard, Amex',
                color: Colors.orangeAccent,
              ),

              const Spacer(),
              
              ElevatedButton(
                onPressed: () {
                  context.go('/home'); // Continue to dashboard
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF5DF22A),
                  foregroundColor: const Color(0xFF163339),
                  padding: const EdgeInsets.symmetric(vertical: 18.0),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                ),
                child: const Text(
                  'Continue to Dashboard',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () {
                  context.go('/home'); // Skip for now
                },
                child: const Text(
                  'Skip for now',
                  style: TextStyle(
                    color: Color(0xFF8BA5A8),
                    fontSize: 16,
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

  Widget _buildConnectionCard(BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF21444A),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: color.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: color, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: Color(0xFF8BA5A8),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: Color(0xFF8BA5A8)),
        ],
      ),
    );
  }
}
