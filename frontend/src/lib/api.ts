const API_BASE = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';
const API_BASE_CLIENT = process.env.NEXT_PUBLIC_API_URL_CLIENT || 'http://5.129.205.143:8000';

export async function fetchArticles(tag?: string) {
  const params = tag ? `?tag=${tag}` : '';
  const res = await fetch(`${API_BASE}/api/v1/articles${params}`, { next: { revalidate: 60 } });
  if (!res.ok) return { items: [], total: 0 };
  return res.json();
}

export async function fetchArticle(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/articles/${slug}`, { next: { revalidate: 60 } });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchAgent(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/agents/${slug}`, { next: { revalidate: 60 } });
  if (!res.ok) return null;
  return res.json();
}

// ── Children / Development Map ─────────────────────────────────────────────────

export interface Child {
  id: string;
  name: string | null;
  birth_date: string;
  gender: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface MapDomain {
  domain: string;
  score: number;
  achieved: number;
  expected: number;
  red_flags: number;
}

export interface DevelopmentMap {
  child_id: string;
  age_months: number;
  domains: MapDomain[];
  overall_score: number;
}

export interface Observation {
  id: string;
  child_id: string;
  domain: string;
  milestone_code: string;
  status: string;
  observed_at: string;
  age_months: number;
  confidence: number;
  source: string;
  norm_text: string | null;
  concern_text: string | null;
  exercises: Array<{title: string; description: string; frequency?: string}> | null;
}

export interface Recommendation {
  id: string;
  child_id: string;
  domain: string;
  activity_title: string;
  activity_description: string;
  target_milestone: string | null;
  priority: string;
  is_red_flag: boolean;
  expires_at: string | null;
}

export interface Milestone {
  code: string;
  domain: string;
  title: string;
  description: string | null;
  age_months_min: number;
  age_months_max: number;
  age_months_concern: number | null;
  source: string;
  norm_text: string | null;
  concern_text: string | null;
  exercises: Array<{title: string; description: string; frequency?: string}> | null;
}

export async function fetchMilestones(domain?: string, age_months?: number): Promise<Milestone[]> {
  const params = new URLSearchParams();
  if (domain) params.set('domain', domain);
  if (age_months !== undefined) params.set('age_months', String(age_months));
  const res = await fetch(`${API_BASE}/api/v1/children/milestones/all?${params}`, { next: { revalidate: 3600 } });
  if (!res.ok) return [];
  return res.json();
}


export async function fetchAgents(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/agents?limit=50`, { next: { revalidate: 300 } })
    if (!res.ok) return []
    const data = await res.json()
    return Array.isArray(data) ? data : (data.items || [])
  } catch { return [] }
}

export async function searchArticles(q: string, limit: number = 20) {
  const res = await fetch(`${API_BASE}/api/v1/articles/search?q=${encodeURIComponent(q)}&limit=${limit}`, { cache: 'no-store' });
  if (!res.ok) return { items: [], total: 0 };
  return res.json();
}
