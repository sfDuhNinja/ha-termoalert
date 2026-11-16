<img src="custom_components/termoalert/brand/icon.png" alt="TermoAlert București" width="96">

# TermoAlert București pentru Home Assistant

Îți spune dacă blocul tău din București are avarie la apa caldă, motivul și când se estimează remedierea.
Datele vin de la [CMTEB – Funcționare sistem termoficare](https://www.cmteb.ro/functionare_sistem_termoficare.php), aceeași sursă ca aplicația TermoAlert. Pagina e citită la fiecare 10 minute.

> Integrare neoficială, fără legătură cu Termoenergetica București (CMTEB).

## Instalare

[![Deschide în Marketplace](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=sfDuhNinja&repository=ha-termoalert&category=integration)

**Marketplace (Home Assistant 2026.11+):** apasă butonul de mai sus, sau Setări → Marketplace → ⋮ → Custom repositories → `https://github.com/sfDuhNinja/ha-termoalert`, categoria *Integration*.

**Manual:** copiază `custom_components/termoalert` în `config/custom_components/` și repornește Home Assistant.

## Configurare

Setări → Dispozitive și servicii → Adaugă integrare → **TermoAlert București**:

| Câmp | Exemplu | Note |
|---|---|---|
| Strada | `Lacul Tei`, `Bd. Lacul Tei`, `Soseaua Pantelimon` | Diacriticele, majusculele și prefixele (Str, Bd, Șos, Calea, Aleea…) nu contează |
| Bloc (opțional) | `5A2`, `bl. 5A2` | Gol = toată strada |

Poți adăuga mai multe adrese (de ex. acasă și la părinți).

## Ce primești

`binary_sensor.<adresa>_avarie_apa_calda`: `on` când e oprire sau deficiență la apa caldă (ACC) pe adresa ta.

| Atribut | Conținut |
|---|---|
| `tip` | ex. „Oprire ACC/INC”, „Deficienta ACC” |
| `motiv` | cauza / descrierea intervenției |
| `estimare_remediere` | data și ora estimată (ISO) |
| `punct_termic` | punctul termic afectat |
| `alte_avarii` | avarii doar la încălzire pe aceeași adresă |

Dacă CMTEB listează o stradă fără blocuri, se consideră afectată toată strada. Intervalele de blocuri („E1-E4”) se potrivesc doar la capete (E1, E4).

## Notificare pe telefon

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.lacul_tei_bl_5a2_avarie_apa_calda
    to: "on"
actions:
  - action: notify.mobile_app_telefonul_meu
    data:
      title: Fără apă caldă
      message: >
        {{ state_attr(trigger.entity_id, 'motiv') }}.
        Estimare: {{ as_datetime(state_attr(trigger.entity_id, 'estimare_remediere')).strftime('%d.%m %H:%M') }}
```

## Licență

MIT
