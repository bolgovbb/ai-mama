"""Seed WHO/CDC developmental milestones into DB."""
import asyncio
import sys
sys.path.insert(0, '/opt/ai-mama/backend')
from app.database import async_session, engine, Base
from app.models.milestone import Milestone

MILESTONES = [
    # SPEECH
    ("speech.cooing", "speech", "Гуление (а-гу)", 1, 3, 4, "WHO"),
    ("speech.babbling", "speech", "Лепет (ба-ба, ма-ма)", 4, 7, 9, "WHO"),
    ("speech.first_words", "speech", "Первые слова (2-3 слова)", 9, 12, 16, "WHO"),
    ("speech.two_words", "speech", "Двухсловные фразы", 18, 24, 30, "WHO"),
    ("speech.sentences", "speech", "Предложения из 3+ слов", 24, 36, 42, "WHO"),
    # MOTOR GROSS
    ("motor_gross.head_control", "motor_gross", "Держит голову (лёжа на животе)", 2, 4, 5, "WHO"),
    ("motor_gross.rolling", "motor_gross", "Переворачивается со спины на живот", 4, 6, 7, "WHO"),
    ("motor_gross.sitting", "motor_gross", "Сидит без опоры", 6, 9, 11, "WHO"),
    ("motor_gross.crawling", "motor_gross", "Ползает на четвереньках", 7, 10, 13, "WHO"),
    ("motor_gross.standing", "motor_gross", "Стоит с опорой", 8, 10, 12, "WHO"),
    ("motor_gross.walking", "motor_gross", "Ходит самостоятельно", 9, 12, 18, "WHO"),
    ("motor_gross.running", "motor_gross", "Бегает", 15, 18, 24, "CDC"),
    ("motor_gross.stairs_up", "motor_gross", "Поднимается по лестнице", 18, 24, 30, "CDC"),
    # MOTOR FINE
    ("motor_fine.grasping", "motor_fine", "Хватает предметы", 3, 5, 7, "WHO"),
    ("motor_fine.pincer_grasp", "motor_fine", "Пинцетный захват", 8, 10, 12, "WHO"),
    ("motor_fine.stacking_blocks", "motor_fine", "Складывает башню из 2 кубиков", 12, 15, 18, "CDC"),
    ("motor_fine.scribbling", "motor_fine", "Каракули карандашом", 15, 18, 24, "CDC"),
    ("motor_fine.page_turn", "motor_fine", "Листает страницы книги", 18, 24, 30, "CDC"),
    # COGNITIVE
    ("cognitive.object_permanence", "cognitive", "Постоянство объекта (ищет спрятанный предмет)", 7, 10, 12, "WHO"),
    ("cognitive.cause_effect", "cognitive", "Причинно-следственные связи (нажимает кнопку)", 9, 12, 15, "CDC"),
    ("cognitive.sorting", "cognitive", "Сортирует предметы по форме", 18, 24, 30, "CDC"),
    ("cognitive.pretend_play", "cognitive", "Сюжетно-ролевая игра", 18, 24, 36, "CDC"),
    ("cognitive.counting_3", "cognitive", "Считает до 3", 24, 36, 42, "CDC"),
    # SOCIAL
    ("social.social_smile", "social", "Социальная улыбка", 1, 2, 3, "WHO"),
    ("social.stranger_anxiety", "social", "Страх незнакомцев", 6, 9, 12, "WHO"),
    ("social.waves_bye", "social", "Машет рукой «пока»", 9, 12, 14, "CDC"),
    ("social.parallel_play", "social", "Игра рядом с другими детьми", 18, 24, 30, "CDC"),
    ("social.cooperative_play", "social", "Совместная игра с другими детьми", 30, 36, 48, "CDC"),
    # EMOTIONAL
    ("emotional.attachment", "emotional", "Привязанность к близким (предпочитает маму)", 4, 7, 9, "WHO"),
    ("emotional.empathy_basic", "emotional", "Базовая эмпатия (реагирует на чужой плач)", 12, 18, 24, "CDC"),
    ("emotional.self_regulation", "emotional", "Начальная саморегуляция (успокаивается)", 18, 24, 36, "CDC"),
]

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as db:
        from sqlalchemy import select
        existing = (await db.execute(select(Milestone))).scalars().all()
        existing_codes = {m.code for m in existing}
        added = 0
        for code, domain, title, mn, mx, concern, source in MILESTONES:
            if code not in existing_codes:
                db.add(Milestone(code=code, domain=domain, title=title,
                    age_months_min=mn, age_months_max=mx,
                    age_months_concern=concern, source=source))
                added += 1
        await db.commit()
        print(f"Seeded {added} milestones, {len(existing_codes)} already existed")

asyncio.run(seed())
