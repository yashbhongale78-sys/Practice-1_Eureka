/**
 * js/realtime.js — Supabase Realtime subscriptions.
 * Subscribe to live updates for complaints and votes.
 *
 * Uses the Supabase JS CDN client directly.
 * Expects window.SUPABASE_URL and window.SUPABASE_ANON_KEY to be set.
 */

let supabaseClient = null;

function getSupabase() {
  if (!supabaseClient) {
    supabaseClient = window.supabase.createClient(
      window.SUPABASE_URL,
      window.SUPABASE_ANON_KEY
    );
  }
  return supabaseClient;
}

/**
 * Subscribe to new complaints being inserted.
 * @param {Function} onInsert - Called with new complaint row
 */
export function subscribeToComplaints(onInsert) {
  const sb = getSupabase();
  return sb
    .channel("public:complaints")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "complaints" },
      (payload) => onInsert(payload.new)
    )
    .on(
      "postgres_changes",
      { event: "UPDATE", schema: "public", table: "complaints" },
      (payload) => {
        // Trigger a UI refresh if status or priority changes
        if (typeof window.onComplaintUpdated === "function") {
          window.onComplaintUpdated(payload.new);
        }
      }
    )
    .subscribe();
}

/**
 * Subscribe to vote changes to update live vote counts.
 * @param {Function} onVote - Called with { complaint_id, count }
 */
export function subscribeToVotes(onVote) {
  const sb = getSupabase();
  return sb
    .channel("public:votes")
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "votes" },
      (payload) => onVote(payload.new)
    )
    .subscribe();
}

/**
 * Remove all active subscriptions.
 */
export function unsubscribeAll() {
  const sb = getSupabase();
  sb.removeAllChannels();
}
