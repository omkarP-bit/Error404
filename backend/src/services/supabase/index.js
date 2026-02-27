import { supabaseAdmin } from '../../config/supabase.js';

class SupabaseService {
  async query(table, options = {}) {
    let query = supabaseAdmin.from(table).select(options.select || '*');

    if (options.eq) {
      Object.entries(options.eq).forEach(([key, value]) => {
        query = query.eq(key, value);
      });
    }

    if (options.order) {
      query = query.order(options.order.column, { ascending: options.order.ascending ?? true });
    }

    if (options.limit) {
      query = query.limit(options.limit);
    }

    const { data, error } = await query;
    if (error) throw error;
    return data;
  }

  async insert(table, data) {
    const { data: result, error } = await supabaseAdmin
      .from(table)
      .insert(data)
      .select()
      .single();
    if (error) throw error;
    return result;
  }

  async update(table, id, data, idColumn = 'id') {
    const { data: result, error } = await supabaseAdmin
      .from(table)
      .update(data)
      .eq(idColumn, id)
      .select()
      .single();
    if (error) throw error;
    return result;
  }

  async delete(table, id, idColumn = 'id') {
    const { error } = await supabaseAdmin
      .from(table)
      .delete()
      .eq(idColumn, id);
    if (error) throw error;
    return true;
  }
}

export default new SupabaseService();
