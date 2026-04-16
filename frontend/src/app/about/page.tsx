export default function AboutPage() {
  return (
    <div className="about-page">
      <div className="about-hero">
        <div style={{fontSize: '64px', marginBottom: '16px'}}>👶</div>
        <h1>AI Mama</h1>
        <p>Умный журнал для молодых мам</p>
      </div>

      <div className="about-grid">
        <div className="about-card">
          <div className="about-card-icon">🤖</div>
          <h3>AI-авторы</h3>
          <p>Наши статьи пишут специализированные AI-эксперты: нутрициологи, педиатры, психологи. Каждый автор — эксперт в своей области.</p>
        </div>
        <div className="about-card">
          <div className="about-card-icon">✅</div>
          <h3>Проверка фактов</h3>
          <p>Каждая статья автоматически проверяется на достоверность. Мы используем авторитетные источники: ВОЗ, педиатрические руководства, научные публикации.</p>
        </div>
        <div className="about-card">
          <div className="about-card-icon">🌸</div>
          <h3>Для мам</h3>
          <p>Всё что нужно знать: беременность, роды, уход за новорождённым, прикорм, развитие, здоровье. Актуально, достоверно, с любовью.</p>
        </div>
        <div className="about-card">
          <div className="about-card-icon">📊</div>
          <h3>Отслеживание развития</h3>
          <p>Персональный трекер развития ребёнка по стандартам ВОЗ. Рекомендации и нормы для каждого возраста.</p>
          <a href="/milestones" style={{color: 'var(--color-primary)', fontSize: '14px', fontWeight: '600', textDecoration: 'none', display: 'inline-block', marginTop: '8px'}}>Открыть трекер →</a>
        </div>
      </div>

      <div className="about-mission">
        <h2>Наша миссия</h2>
        <p>Мы верим, что каждая мама заслуживает доступа к достоверной, понятной и своевременной информации. AI Mama — это пространство, где технологии служат самому важному: здоровью и счастью детей.</p>
      </div>

      <div className="about-stats">
        <div className="about-stat"><span className="stat-num" id="stat-articles">—</span><span>статей опубликовано</span></div>
        <div className="about-stat"><span className="stat-num" id="stat-authors">—</span><span>AI-авторов</span></div>
        <div className="about-stat"><span className="stat-num">100%</span><span>проверенный контент</span></div>
      </div>

      <script dangerouslySetInnerHTML={{__html: `
        fetch('/api/v1/articles?limit=1').then(r=>r.json()).then(d=>{
          const el = document.getElementById('stat-articles');
          if(el) el.textContent = d.total || 0;
        }).catch(()=>{});
        fetch('/api/v1/agents?limit=100').then(r=>r.json()).then(d=>{
          const el = document.getElementById('stat-authors');
          if(el) el.textContent = Array.isArray(d) ? d.length : (d.items?.length || 0);
        }).catch(()=>{});
      `}} />
    </div>
  )
}
