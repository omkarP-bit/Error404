import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'dashboard.dart';
import 'expenses.dart';
import 'goals.dart';
import 'insights.dart';
import 'profile.dart';
import 'start.dart';
import 'signup.dart';
import 'verify_otp.dart';
import 'bankacc.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');
final GlobalKey<NavigatorState> _shellNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'shell');

final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/home', // BYPASS AUTH FOR NOW
  routes: [
    GoRoute(
      path: '/start',
      builder: (context, state) => const StartScreen(),
    ),
    GoRoute(
      path: '/signup',
      builder: (context, state) => const SignupScreen(),
    ),
    GoRoute(
      path: '/verify',
      builder: (context, state) {
        final email = state.extra as String? ?? '';
        return VerifyOtpScreen(email: email);
      },
    ),
    GoRoute(
      path: '/bankacc',
      builder: (context, state) => const BankAccScreen(),
    ),
    ShellRoute(
      navigatorKey: _shellNavigatorKey,
      builder: (context, state, child) {
        return AppShellScaffold(child: child);
      },
      routes: [
        GoRoute(
          path: '/home',
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: '/expenses',
          builder: (context, state) => const ExpensesScreen(),
        ),
        GoRoute(
          path: '/goals',
          builder: (context, state) => const GoalsScreen(),
        ),
        GoRoute(
          path: '/insights',
          builder: (context, state) => const InsightsScreen(),
        ),
        GoRoute(
          path: '/profile',
          builder: (context, state) => const ProfileScreen(),
        ),
      ],
    ),
  ],
);

class AppShellScaffold extends StatelessWidget {
  const AppShellScaffold({Key? key, required this.child}) : super(key: key);

  final Widget child;

  static const Color headerColor = Color(0xFF163339);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent, // Background colors handled by child screens
      body: child,
      bottomNavigationBar: _buildBottomNavigationBar(context),
    );
  }

  Widget _buildBottomNavigationBar(BuildContext context) {
    final String location = GoRouterState.of(context).uri.path;

    int _getSelectedIndex() {
      if (location.startsWith('/home')) return 0;
      if (location.startsWith('/expenses')) return 1;
      if (location.startsWith('/goals')) return 2;
      if (location.startsWith('/insights')) return 3;
      if (location.startsWith('/profile')) return 4;
      return 0;
    }

    return Container(
      decoration: BoxDecoration(
        color: headerColor,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(30),
          topRight: Radius.circular(30),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 20,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 12.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildBottomNavItem(
                context,
                icon: Icons.home_filled,
                label: 'Home',
                index: 0,
                selectedIndex: _getSelectedIndex(),
                route: '/home',
              ),
              _buildBottomNavItem(
                context,
                icon: Icons.credit_card_outlined,
                label: 'Expenses',
                index: 1,
                selectedIndex: _getSelectedIndex(),
                route: '/expenses',
              ),
              _buildBottomNavItem(
                context,
                icon: Icons.track_changes_outlined,
                label: 'Goals',
                index: 2,
                selectedIndex: _getSelectedIndex(),
                route: '/goals',
              ),
              _buildBottomNavItem(
                context,
                icon: Icons.insights_outlined, // Psychology could also work, matching designs
                label: 'Insights',
                index: 3,
                selectedIndex: _getSelectedIndex(),
                route: '/insights',
              ),
               _buildBottomNavItem(
                context,
                icon: Icons.person_outline,
                label: 'Profile',
                index: 4,
                selectedIndex: _getSelectedIndex(),
                route: '/profile',
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBottomNavItem(
    BuildContext context, {
    required IconData icon,
    required String label,
    required int index,
    required int selectedIndex,
    required String route,
  }) {
    final bool isSelected = index == selectedIndex;
    const Color activeColor = Color(0xFF7CFC00); // Neon green
    const Color inactiveColor = Color(0xFF8BA5A8); // Muted grey

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () {
        context.go(route);
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: isSelected
                ? BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeColor.withOpacity(0.15),
                    boxShadow: [
                      BoxShadow(
                        color: activeColor.withOpacity(0.2),
                        blurRadius: 15,
                        spreadRadius: 2,
                      )
                    ],
                  )
                : const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.transparent,
                  ),
            child: Icon(
              icon,
              color: isSelected ? activeColor : inactiveColor,
              size: 26,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: isSelected ? activeColor : inactiveColor,
              fontSize: 12,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
