/*
  Réglage du temps réel (visiteurs en ligne, avatars des autres visiteurs, chat).

  1. Créer un projet gratuit sur https://supabase.com (un projet à part, pas celui d'une autre application).
  2. Dans Project Settings > API, copier « Project URL » et la clé « anon public » (ou « publishable »).
  3. Les coller ci-dessous. Cette clé est faite pour être publique : elle peut être dans le dépôt.
     Jamais la clé « service_role » ni une clé « secret ».

  Rien n'est écrit dans la base : seul le canal temps réel ci-dessous est utilisé (Presence et Broadcast).
  Laisser vide pour désactiver : le compteur et le chat restent alors cachés.
*/
export const MULTIJOUEUR = {
  url: "https://twidouwbbikvqqghnhdp.supabase.co",
  cleAnon: "sb_publishable_97QN2ukZMBJ62Nv5ROygxw_euwfHKtr",
  canal: "royaume-ernest",
};
