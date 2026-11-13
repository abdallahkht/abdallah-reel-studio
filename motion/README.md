# موشن عربي — ملفات تقدر تعدّلها

ثلاثة قوالب أصلية كبداية: **عنوان، رقم مهم، وثلاث خطوات**. غيّر النص والألوان والمدة من JSON. اطلب من Claude أو Codex التعديل بدل كتابة الإعدادات بنفسك.

شاهد [الأمثلة](../examples/README.md). هذه مشاهد كاملة للفيديو، وليست مؤثرات عزل شخص أو خلفيات شفافة.

## تجهيز مرة واحدة

من مجلد المشروع:

```sh
python3 setup.py --motion
```

## إخراج فيديو

على Mac وLinux:

```sh
.venv/bin/python motion/render.py motion/templates/title.json --output _deploy/my-title.mp4
```

على Windows:

```powershell
.venv\Scripts\python.exe motion\render.py motion\templates\title.json --output _deploy\my-title.mp4
```

تقدر تستخدم `metric.json` أو `steps.json`. النتيجة MP4 ومعه صورة PNG للمراجعة. إذا الاسم موجود، اختر اسماً جديداً. الفيديو صامت لتضيف صوتك أو موسيقاك أثناء المونتاج.

| الخيار | الاستخدام |
|---|---|
| `--width 1080` | عرض الفيديو؛ المتاح 540 أو 720 أو 1080، والنسبة دائماً 9:16 |
| `--fps 30` | عدد الإطارات؛ المتاح 24 أو 25 أو 30 أو 50 أو 60 |
| `--font /path/to/font.ttf` | خط عربي موجود على جهازك؛ لا يأتي أي ملف خط تجاري مع المشروع |

غيّر `footer` لاسمك أو اجعله نصاً فارغاً لإزالة الاسم من الفيديو.

الحقول المشتركة: `title`، `eyebrow`، `accent`، `background`، `duration` بالثواني. قالب العنوان يستخدم `subtitle`، وقالب الرقم يستخدم `value` و`subtitle`، وقالب الخطوات يستخدم قائمة `steps` حتى ثلاث خطوات. إذا النص أطول من المساحة، قصّره أو قسّمه على مشهدين.

المكتبات تثبّت داخل `.venv` فقط. [Pillow](https://pillow.readthedocs.io/) للرسم، [Arabic Reshaper](https://pypi.org/project/arabic-reshaper/) و[Python BiDi](https://pypi.org/project/python-bidi/) لعرض العربية. FFmpeg يحوّل الإطارات إلى فيديو. حقوق كل مكتبة تبقى لأصحابها؛ ملفاتها ليست مضمّنة في التنزيل.
