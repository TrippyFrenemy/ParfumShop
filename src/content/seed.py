from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models import SiteContent

# (page, key, published_value, label, content_type)
INITIAL_CONTENT: list[tuple[str, str, str, str, str]] = [
    # ========================= global (base.html) =========================
    ("global", "global.nav_catalog", "Каталог", "Навiгацiя: Каталог", "short"),
    ("global", "global.nav_orders", "Замовлення", "Навiгацiя: Замовлення", "short"),
    ("global", "global.nav_cart", "Кошик", "Навiгацiя: Кошик", "short"),
    ("global", "global.nav_contacts", "Контакти", "Навiгацiя: Контакти", "short"),
    ("global", "global.nav_login", "Увiйти", "Навiгацiя: Увiйти", "short"),
    ("global", "global.nav_register", "Реєстрацiя", "Навiгацiя: Реєстрацiя", "short"),
    ("global", "global.nav_logout", "Вийти", "Навiгацiя: Вийти", "short"),
    ("global", "global.nav_admin", "Адмiн-панель", "Навiгацiя: Адмiн-панель", "short"),
    ("global", "global.nav_my_orders", "Мої замовлення", "Навiгацiя: Мої замовлення", "short"),
    ("global", "global.search_placeholder", "Пошук парфумiв...", "Пошук: плейсхолдер", "short"),
    ("global", "global.cart_drawer_title", "Кошик", "Мiнi-кошик: заголовок", "short"),
    ("global", "global.cart_drawer_empty", "Кошик порожнiй", "Мiнi-кошик: пустий", "short"),
    ("global", "global.cart_drawer_total", "Разом:", "Мiнi-кошик: разом", "short"),
    ("global", "global.cart_drawer_checkout", "Оформити замовлення", "Мiнi-кошик: оформити", "short"),
    ("global", "global.cart_drawer_view", "Переглянути кошик", "Мiнi-кошик: переглянути", "short"),
    ("global", "global.footer_tagline", "Iнтернет-магазин оригiнальної парфумерiї. Найкращi аромати вiд провiдних брендiв.", "Футер: опис", "text"),
    ("global", "global.footer_nav_heading", "Навiгацiя", "Футер: заголовок навiгацiї", "short"),
    ("global", "global.footer_info_heading", "Iнформацiя", "Футер: заголовок iнформацiї", "short"),
    ("global", "global.footer_contacts_heading", "Контакти", "Футер: заголовок контактiв", "short"),
    ("global", "global.footer_nav_home", "Головна", "Футер: Головна", "short"),
    ("global", "global.footer_delivery_payment", "Доставка та оплата", "Футер: Доставка та оплата", "short"),
    ("global", "global.footer_returns", "Повернення товару", "Футер: Повернення товару", "short"),
    ("global", "global.footer_about", "Про нас", "Футер: Про нас", "short"),
    ("global", "global.footer_copyright", "ParfumShop. Всi права захищенi.", "Футер: копiрайт", "short"),

    # ========================= home (index.html) =========================
    ("home", "home.hero_title", 'Ваш iдеальний <span class="text-brand-400">аромат</span> чекає', "Герой: заголовок", "html"),
    ("home", "home.hero_subtitle", "Оригiнальна парфумерiя вiд провiдних свiтових брендiв. Безкоштовна доставка вiд 1000 грн.", "Герой: пiдзаголовок", "text"),
    ("home", "home.hero_cta_catalog", "Перейти до каталогу", "Герой: кнопка каталог", "short"),
    ("home", "home.hero_cta_contacts", "Контакти", "Герой: кнопка контакти", "short"),
    ("home", "home.feature_1_title", "100% оригiнал", "Переваги 1: заголовок", "short"),
    ("home", "home.feature_1_subtitle", "Гарантiя якостi", "Переваги 1: пiдпис", "short"),
    ("home", "home.feature_2_title", "Швидка доставка", "Переваги 2: заголовок", "short"),
    ("home", "home.feature_2_subtitle", "Нова Пошта / Укрпошта", "Переваги 2: пiдпис", "short"),
    ("home", "home.feature_3_title", "Зручна оплата", "Переваги 3: заголовок", "short"),
    ("home", "home.feature_3_subtitle", "На ФОП рахунок", "Переваги 3: пiдпис", "short"),
    ("home", "home.feature_4_title", "Оптовi цiни", "Переваги 4: заголовок", "short"),
    ("home", "home.feature_4_subtitle", "Знижки вiд 5 шт", "Переваги 4: пiдпис", "short"),
    ("home", "home.categories_heading", "Категорiї", "Секцiя: Категорiї", "short"),
    ("home", "home.categories_link", "Усi категорiї", "Посилання: усi категорiї", "short"),
    ("home", "home.featured_heading", "Акцiйнi пропозицiї", "Секцiя: Акцiї", "short"),
    ("home", "home.featured_link", "Усi акцiї", "Посилання: усi акцiї", "short"),
    ("home", "home.new_heading", "Новинки", "Секцiя: Новинки", "short"),
    ("home", "home.new_link", "Дивитись усi", "Посилання: дивитись усi", "short"),
    ("home", "home.cta_heading", "Оптовi замовлення", "CTA: заголовок", "short"),
    ("home", "home.cta_text", "Спецiальнi цiни при замовленнi вiд 5 одиниць. Звернiться до нас для iндивiдуальної пропозицiї.", "CTA: текст", "text"),
    ("home", "home.cta_button", "Зв'язатися з нами", "CTA: кнопка", "short"),

    # ========================= contacts =========================
    ("contacts", "contacts.page_title", "Контакти", "Заголовок сторiнки", "short"),
    ("contacts", "contacts.contact_heading", "Зв'язатися з нами", "Пiдзаголовок: зв'язок", "short"),
    ("contacts", "contacts.phone_label", "Телефон", "Лейбл: телефон", "short"),
    ("contacts", "contacts.email_label", "Email", "Лейбл: email", "short"),
    ("contacts", "contacts.about_heading", "Про нас", "Заголовок: про нас", "short"),
    ("contacts", "contacts.delivery_heading", "Доставка", "Заголовок: доставка", "short"),
    ("contacts", "contacts.np_name", "Нова Пошта", "Доставка: Нова Пошта", "short"),
    ("contacts", "contacts.np_text", "Доставка по всiй Українi 1-3 робочi днi. Вiдправка протягом 1-2 днiв пiсля пiдтвердження.", "Доставка: текст НП", "text"),
    ("contacts", "contacts.ukr_name", "Укрпошта", "Доставка: Укрпошта", "short"),
    ("contacts", "contacts.ukr_text", "Доставка 3-7 робочих днiв.", "Доставка: текст УП", "text"),
    ("contacts", "contacts.payment_heading", "Оплата", "Заголовок: оплата", "short"),
    ("contacts", "contacts.payment_default", "Оплата на ФОП рахунок.", "Оплата: текст за замовчуванням", "text"),
    ("contacts", "contacts.returns_heading", "Повернення товару", "Заголовок: повернення", "short"),
    ("contacts", "contacts.returns_text", "Для повернення або обмiну товару зв'яжiться з нами за телефоном або email. Повернення можливе протягом 14 днiв з моменту отримання замовлення за умови збереження товарного вигляду та упаковки.", "Текст: повернення", "text"),

    # ========================= catalog =========================
    ("catalog", "catalog.filters_heading", "Фiльтри", "Заголовок: фiльтри", "short"),
    ("catalog", "catalog.categories_label", "Категорiї", "Лейбл: категорiї", "short"),
    ("catalog", "catalog.all_products", "Усi товари", "Лейбл: усi товари", "short"),
    ("catalog", "catalog.price_label", "Цiна, грн", "Лейбл: цiна", "short"),
    ("catalog", "catalog.price_from", "Вiд", "Плейсхолдер: вiд", "short"),
    ("catalog", "catalog.price_to", "До", "Плейсхолдер: до", "short"),
    ("catalog", "catalog.brand_label", "Бренд", "Лейбл: бренд", "short"),
    ("catalog", "catalog.all_brands", "Усi бренди", "Лейбл: усi бренди", "short"),
    ("catalog", "catalog.apply_button", "Застосувати", "Кнопка: застосувати", "short"),
    ("catalog", "catalog.sort_newest", "Новинки", "Сортування: новинки", "short"),
    ("catalog", "catalog.sort_price_asc", "Спочатку дешевшi", "Сортування: дешевшi", "short"),
    ("catalog", "catalog.sort_price_desc", "Спочатку дорожчi", "Сортування: дорожчi", "short"),
    ("catalog", "catalog.sort_name", "За назвою", "Сортування: за назвою", "short"),
    ("catalog", "catalog.empty_text", "Товарiв не знайдено", "Порожнiй стан: текст", "short"),
    ("catalog", "catalog.empty_link", "Переглянути весь каталог", "Порожнiй стан: посилання", "short"),
    ("catalog", "catalog.found_label", "Знайдено:", "Лейбл: знайдено", "short"),
    ("catalog", "catalog.add_to_cart", "В кошик", "Кнопка: додати в кошик", "short"),
    ("catalog", "catalog.search_label", "Пошук:", "Лейбл: пошук", "short"),
    ("catalog", "catalog.search_reset", "Скинути", "Посилання: скинути пошук", "short"),

    # ========================= product detail =========================
    ("product", "product.wholesale_heading", "Оптовi цiни:", "Заголовок: оптовi цiни", "short"),
    ("product", "product.in_stock", "В наявностi", "Статус: в наявностi", "short"),
    ("product", "product.out_of_stock", "Немає в наявностi", "Статус: немає", "short"),
    ("product", "product.add_to_cart", "Додати до кошика", "Кнопка: додати до кошика", "short"),
    ("product", "product.description_heading", "Опис", "Заголовок: опис", "short"),
    ("product", "product.delivery_heading", "Доставка", "Заголовок: доставка", "short"),
    ("product", "product.np_label", "Нова Пошта", "Доставка: НП", "short"),
    ("product", "product.np_text", "Доставка 1-3 днi по Українi", "Доставка: текст НП", "short"),
    ("product", "product.ukr_label", "Укрпошта", "Доставка: УП", "short"),
    ("product", "product.ukr_text", "Доставка 3-7 днiв", "Доставка: текст УП", "short"),

    # ========================= cart =========================
    ("cart", "cart.page_title", "Кошик", "Заголовок сторiнки", "short"),
    ("cart", "cart.total_label", "Разом:", "Лейбл: разом", "short"),
    ("cart", "cart.checkout_button", "Оформити замовлення", "Кнопка: оформити", "short"),
    ("cart", "cart.continue_shopping", "Продовжити покупки", "Посилання: продовжити", "short"),
    ("cart", "cart.empty_text", "Ваш кошик порожнiй", "Порожнiй стан: текст", "short"),
    ("cart", "cart.empty_cta", "Перейти до каталогу", "Порожнiй стан: кнопка", "short"),

    # ========================= checkout =========================
    ("checkout", "checkout.page_title", "Оформлення замовлення", "Заголовок сторiнки", "short"),
    ("checkout", "checkout.contact_heading", "Контактнi данi", "Заголовок: контакти", "short"),
    ("checkout", "checkout.name_label", "ПIБ", "Лейбл: ПIБ", "short"),
    ("checkout", "checkout.phone_label", "Телефон", "Лейбл: телефон", "short"),
    ("checkout", "checkout.email_label", "Email", "Лейбл: email", "short"),
    ("checkout", "checkout.delivery_heading", "Доставка", "Заголовок: доставка", "short"),
    ("checkout", "checkout.np_label", "Нова Пошта", "Доставка: НП", "short"),
    ("checkout", "checkout.np_days", "1-3 днi", "Доставка: термiн НП", "short"),
    ("checkout", "checkout.ukr_label", "Укрпошта", "Доставка: УП", "short"),
    ("checkout", "checkout.ukr_days", "3-7 днiв", "Доставка: термiн УП", "short"),
    ("checkout", "checkout.city_label", "Мiсто", "Лейбл: мiсто", "short"),
    ("checkout", "checkout.warehouse_label", "Вiддiлення", "Лейбл: вiддiлення", "short"),
    ("checkout", "checkout.comment_heading", "Коментар", "Заголовок: коментар", "short"),
    ("checkout", "checkout.order_summary", "Ваше замовлення", "Заголовок: пiдсумок", "short"),
    ("checkout", "checkout.coupon_placeholder", "Промокод", "Плейсхолдер: промокод", "short"),
    ("checkout", "checkout.apply_coupon", "Застосувати", "Кнопка: застосувати купон", "short"),
    ("checkout", "checkout.items_total", "Сума товарiв:", "Лейбл: сума товарiв", "short"),
    ("checkout", "checkout.discount_label", "Знижка:", "Лейбл: знижка", "short"),
    ("checkout", "checkout.pay_total", "До сплати:", "Лейбл: до сплати", "short"),
    ("checkout", "checkout.payment_heading", "Оплата:", "Заголовок: оплата", "short"),
    ("checkout", "checkout.city_placeholder", "Почнiть вводити назву мiста...", "Плейсхолдер: мiсто НП", "short"),
    ("checkout", "checkout.warehouse_placeholder", "Спочатку оберiть мiсто", "Плейсхолдер: вiддiлення", "short"),
    ("checkout", "checkout.up_city_placeholder", "Назва мiста", "Плейсхолдер: мiсто УП", "short"),
    ("checkout", "checkout.address_label", "Адреса (вiддiлення або поштова адреса)", "Лейбл: адреса", "short"),
    ("checkout", "checkout.address_placeholder", "вул. Хрещатик 1 або Вiддiлення №5", "Плейсхолдер: адреса", "short"),
    ("checkout", "checkout.np_to_warehouse", "До вiддiлення", "НП: до вiддiлення", "short"),
    ("checkout", "checkout.np_to_address", "Адресна доставка", "НП: адресна доставка", "short"),
    ("checkout", "checkout.np_address_placeholder", "вул. Хрещатик 1, кв. 10", "Плейсхолдер: адреса НП", "short"),
    ("checkout", "checkout.comment_placeholder", "Додаткова iнформацiя до замовлення...", "Плейсхолдер: коментар", "short"),
    ("checkout", "checkout.submit_button", "Оформити замовлення", "Кнопка: оформити", "short"),

    # ========================= orders (my_orders) =========================
    ("orders", "orders.page_title", "Мої замовлення", "Заголовок сторiнки", "short"),
    ("orders", "orders.ttn_label", "ТТН:", "Лейбл: ТТН", "short"),
    ("orders", "orders.empty_text", "У вас ще немає замовлень", "Порожнiй стан: текст", "short"),
    ("orders", "orders.empty_cta", "Перейти до каталогу", "Порожнiй стан: кнопка", "short"),

    # ========================= order confirmation =========================
    ("order_confirm", "order_confirm.success_title", "Замовлення оформлено!", "Успiх: заголовок", "short"),
    ("order_confirm", "order_confirm.success_text", "Дякуємо за ваше замовлення. Ми зв'яжемося з вами найближчим часом.", "Успiх: текст", "text"),
    ("order_confirm", "order_confirm.order_number_label", "Номер замовлення", "Лейбл: номер", "short"),
    ("order_confirm", "order_confirm.items_heading", "Товари", "Заголовок: товари", "short"),
    ("order_confirm", "order_confirm.items_total_label", "Сума товарiв:", "Лейбл: сума", "short"),
    ("order_confirm", "order_confirm.discount_label", "Знижка:", "Лейбл: знижка", "short"),
    ("order_confirm", "order_confirm.grand_total_label", "Всього:", "Лейбл: всього", "short"),
    ("order_confirm", "order_confirm.delivery_heading", "Доставка", "Заголовок: доставка", "short"),
    ("order_confirm", "order_confirm.contact_heading", "Контактна iнформацiя", "Заголовок: контакти", "short"),
    ("order_confirm", "order_confirm.ttn_label", "ТТН:", "Лейбл: ТТН", "short"),
    ("order_confirm", "order_confirm.comment_label", "Коментар:", "Лейбл: коментар", "short"),
    ("order_confirm", "order_confirm.back_to_catalog", "Повернутися до каталогу", "Посилання: назад", "short"),

    # ========================= auth =========================
    ("auth", "auth.login_title", "Увiйти до системи", "Вхiд: заголовок", "short"),
    ("auth", "auth.google_login", "Увiйти через Google", "Вхiд: Google", "short"),
    ("auth", "auth.or_separator", "або", "Роздiлювач: або", "short"),
    ("auth", "auth.email_label", "Email", "Лейбл: email", "short"),
    ("auth", "auth.password_label", "Пароль", "Лейбл: пароль", "short"),
    ("auth", "auth.login_button", "Увiйти", "Кнопка: увiйти", "short"),
    ("auth", "auth.no_account", "Немає акаунту?", "Текст: немає акаунту", "short"),
    ("auth", "auth.register_link", "Реєстрацiя", "Посилання: реєстрацiя", "short"),
    ("auth", "auth.register_title", "Створити акаунт", "Реєстрацiя: заголовок", "short"),
    ("auth", "auth.google_register", "Зареєструватися через Google", "Реєстрацiя: Google", "short"),
    ("auth", "auth.name_label", "Iм'я", "Лейбл: iм'я", "short"),
    ("auth", "auth.register_button", "Створити акаунт", "Кнопка: створити", "short"),
    ("auth", "auth.has_account", "Вже є акаунт?", "Текст: є акаунт", "short"),
    ("auth", "auth.login_link", "Увiйти", "Посилання: увiйти", "short"),
]


async def seed_content(session: AsyncSession) -> None:
    """Insert initial content entries if they don't exist yet. Idempotent."""
    now = datetime.utcnow()
    rows = [
        dict(
            key=key,
            page=page,
            label=label,
            content_type=ctype,
            published_value=value,
            draft_value=None,
            has_unpublished_changes=False,
            updated_at=now,
        )
        for page, key, value, label, ctype in INITIAL_CONTENT
    ]

    if rows:
        stmt = pg_insert(SiteContent).values(rows).on_conflict_do_nothing(index_elements=["key"])
        await session.execute(stmt)
        await session.commit()
