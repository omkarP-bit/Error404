import 'package:supabase_flutter/supabase_flutter.dart';

class AuthService {
  final SupabaseClient _supabase = Supabase.instance.client;

  Future<void> signUpWithOtp(String email) async {
    await _supabase.auth.signInWithOtp(
      email: email,
      shouldCreateUser: true,
    );
  }

  Future<void> verifyOtp(String email, String otp) async {
    await _supabase.auth.verifyOTP(
      email: email,
      token: otp,
      type: OtpType.email,
    );
  }

  Future<void> resendOtp(String email) async {
    await _supabase.auth.resend(
      type: OtpType.email,
      email: email,
    );
  }

  Future<Session?> getSession() async {
    final session = _supabase.auth.currentSession;
    return session;
  }

  Future<void> signOut() async {
    await _supabase.auth.signOut();
  }
}
