# 00 — STRICT EXECUTION RULES

> Canonical governance file for the **MobileChatGpt** development project.
> The canonical planning source is this GitHub repository on `main`.

Սա MobileChatGpt նախագծի պարտադիր execution protocol-ն է։ Բոլոր հաջորդ աշխատանքային chat-երը/agent-ները պետք է հետևեն այս կանոններին մինչև նախագծի ավարտը։

## 1. ՊԱՐՏԱԴԻՐ ՍԿԻԶԲ

Յուրաքանչյուր նոր աշխատանքային session ցանկացած project գործողությունից առաջ պետք է կարդա repo root-ի canonical փաստաթղթերը այս հերթականությամբ՝

1. `00_STRICT_EXECUTION_RULES.md`
2. `01_MASTER_PLAN.md`
3. `02_CURRENT_CHECKPOINT.md`

Եթե այս երեքից որևէ մեկը հասանելի չէ, չի թույլատրվում հորինել project state-ը կամ սկսել նոր ուղղություն։ Պետք է նշել blocker-ը։

## 2. ՊԼԱՆԸ SOURCE OF TRUTH Է

`01_MASTER_PLAN.md`-ը նախագծի պաշտոնական պլանն է։ Չի թույլատրվում ինքնուրույն փոխել product direction-ը, architecture-ը, phase order-ը, MVP scope-ը կամ ընդունված տեխնիկական որոշումները։ Փոփոխություն կարելի է անել միայն օգտատիրոջ հստակ հաստատմամբ։

## 3. ՉՇԵՂՎԵԼ ԸՆԹԱՑԻԿ CHECKPOINT-ԻՑ

`02_CURRENT_CHECKPOINT.md`-ը ցույց է տալիս վերջին հաստատված վիճակը և հաջորդ չավարտված checkpoint-ը։ Նոր chat/agent-ը պետք է շարունակի հենց առաջին չավարտված checkpoint-ից։ Չի կարելի կրկնել արդեն DONE աշխատանքը կամ ցատկել ավելի ուշ phase, եթե ներկայիս քայլը blocked չէ։

## 4. DEVIATION CONTROL

Եթե agent-ը գտնում է ավելի լավ գաղափար, նոր technology կամ այլ architecture, դա չի կարող ավտոմատ փոխարինել ընթացիկ պլանին։ Այն կարելի է գրանցել որպես առաջարկ/backlog։ Պլանից շեղում իրականացնել միայն օգտատիրոջ explicit approval-ից հետո։

## 5. «Շ» ՀՐԱՀԱՆԳԻ ԻՄԱՍՏԸ

Այս նախագծում «Շ» կամ «Շարունակի» նշանակում է՝ շարունակել անմիջապես ընթացիկ չավարտված checkpoint-ը՝ առանց արդեն լուծված հարցերը նորից տալու։ Հարց տալ միայն այն դեպքում, երբ իրական blocker կա՝ օրինակ պարտադիր credential, user approval, անվտանգության սահմանափակում կամ արտաքին գործողություն, որը չի կարող կատարվել առկա գործիքներով։

## 6. EXECUTION > BRAINSTORMING

Եթե պլանը բավարար է իրականացման համար, chat/agent-ը պետք է կատարի աշխատանքը՝ code, artifact, test, integration կամ այլ չափելի արդյունք ստեղծելով։ Չի թույլատրվում վերադառնալ լայն brainstorming-ի, եթե դա checkpoint-ի պարտադիր մասն չէ։

## 7. DONE-Ի ՍԱՀՄԱՆՈՒՄ

Checkpoint-ը DONE է միայն երբ՝

- պահանջվող implementation/artifact-ը ստեղծված է,
- հնարավոր validation/tests-ը անցել են,
- արդյունքը commit/push է արված համապատասխան project storage-ում,
- `02_CURRENT_CHECKPOINT.md`-ը թարմացված է,
- կարևոր որոշումները/փոփոխությունները commit history-ում կամ համապատասխան build notes-ում durable են։

## 8. DURABLE STATE

Chat history-ը source of truth չէ։

- **MobileChatGpt development plan/governance/handoff state** → այս GitHub repository-ի `main` branch-ի canonical `00/01/02` ֆայլերը։
- **MobileChatGpt product runtime project state** → Project Brain PostgreSQL database-ը։
- Google Drive-ը կարող է պահպանվել որպես archive/reference, բայց չի override անում GitHub canonical planning state-ը։

## 9. RISK / APPROVAL

High-impact կամ irreversible գործողությունները չեն կատարվում առանց user approval-ի։ Սակայն approval-ին սպասելիս անկախ safe tasks-ը պետք է շարունակվեն, եթե dependency graph-ը դա թույլ է տալիս։

## 10. SESSION HANDOFF

Յուրաքանչյուր meaningful աշխատանքային session-ի վերջում պետք է հստակ ֆիքսել՝ ինչ DONE է, ինչ FAILED/BLOCKED է, ինչ artifact/test է ստեղծվել, և որն է հաջորդ checkpoint-ը։ Այդ վիճակը պետք է commit արվի `02_CURRENT_CHECKPOINT.md`-ում։

## 11. ԱՌԱՋՆԱՅԻՆՈՒԹՅՈՒՆՆԵՐ

Եթե կան հակասող առաջարկներ կամ աղբյուրներ, առաջնահերթության կարգը սա է՝

1. օգտատիրոջ վերջին explicit հրահանգը,
2. `00_STRICT_EXECUTION_RULES.md`,
3. `01_MASTER_PLAN.md`,
4. `02_CURRENT_CHECKPOINT.md`,
5. implementation specs, source code, tests և build notes,
6. archive/reference նյութերը, այդ թվում Google Drive-ի հին պատճենները։

## 12. ԳԼԽԱՎՈՐ ԿԱՆՈՆ

**Շարժվել մինչև վերջ ըստ հաստատված պլանի։ Չշեղվել, չվերապլանավորել և չփոխել ուղղությունը առանց օգտատիրոջ հստակ թույլտվության։**
