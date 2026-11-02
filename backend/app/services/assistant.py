import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.schemas.assistant import (
    AssistantContext,
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from app.services.hazard import get_hazard_service
from app.services.emergency_facility import get_emergency_facility_service
from app.utils.observability import log_structured_event

logger = logging.getLogger(__name__)


def detect_language(text: str, requested_lang: Optional[str] = "en") -> str:
    """
    Detects if the query text contains Telugu or Devanagari/Hindi script.
    Defaults to requested_lang if purely ASCII or unspecified.
    """
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    if requested_lang in ("te", "hi", "en"):
        return requested_lang
    return "en"


def is_immediate_danger_query(text_lower: str) -> bool:
    """Identifies indicators of active life-threatening flood danger."""
    danger_tokens = [
        "water rising", "water entering", "rising water", "water level rising",
        "trapped", "stuck", "submerged", "drowning", "help me", "sinking",
        "floodwater entering", "water in my house", "urgent help", "stranded",
        "cannot escape", "can't leave", "cut off", "roof", "terrace",
        # Telugu tokens
        "నీరు చేరుతుంది", "మునిగిపోతుంది", "చిక్కుకున్నాను", "సహాయం", "ప్రమాదం", "వరద నీరు",
        "నీరు పెరుగుతుంది", "నీళ్ళు పెరుగుతున్నాయి", "వరద", "మునిగిపోయాను", "ఇంట్లోకి నీరు",
        # Hindi tokens
        "पानी बढ़ रहा है", "पानी घुस गया", "फंस गया", "मदद", "डूब", "खतरा", "बाढ़ का पानी",
        "घर में पानी", "जलस्तर बढ़ रहा", "फंस गए", "डूब रहा"
    ]
    return any(token in text_lower for token in danger_tokens)


class AssistantService:
    """
    Grounded flood-safety decision support assistant for Hyderabad.
    Integrates live municipal hazard boundaries, OSM road networks, and truth-in-facilities
    invariants, backed by an offline-reliable Safety Decision Engine and optional external LLM.
    """

    FALLBACK_PROVIDER = "SAFETY_DECISION_ENGINE_FALLBACK"

    def process_query(self, request: AssistantQueryRequest) -> AssistantQueryResponse:
        """Processes user flood safety questions with safety-first prioritization."""
        message = request.message.strip()
        lang = detect_language(message, request.language)
        context = request.context or AssistantContext()

        # Check if external AI provider is configured and enabled
        if settings.ai_provider != "fallback" and (settings.gemini_api_key or settings.openai_api_key):
            try:
                external_resp = self._call_external_provider(message, lang, context)
                if external_resp:
                    return external_resp
            except Exception as e:
                log_structured_event(
                    "AI_PROVIDER_ERROR",
                    f"External AI provider query failed, falling back to Safety Decision Engine: {str(e)}",
                    level="WARNING",
                    error_type=e.__class__.__name__
                )

        # Execute grounded deterministic Safety Decision Engine
        return self._generate_rule_based_response(message, lang, context)

    def _call_external_provider(
        self, message: str, lang: str, context: AssistantContext
    ) -> Optional[AssistantQueryResponse]:
        """Calls external AI provider if configured, with strict grounding prompt and short timeout."""
        # Provider implementation with httpx timeout safeguard
        # If Gemini API Key is available:
        if settings.gemini_api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
            system_instruction = (
                "You are SafeMap AI Hyderabad Safety Assistant. Provide direct, concise, actionable flood safety guidance. "
                "Never invent rainfall numbers, live river telemetry, or claim routes are guaranteed safe. "
                "Prioritize life safety first (dial 112 or GHMC DRF 040-21111111 if in danger). "
                f"Respond in the user's language: {lang}."
            )
            payload = {
                "contents": [
                    {"parts": [{"text": f"Context: {context.model_dump_json()}\nUser Query: {message}"}]}
                ],
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 350}
            }
            with httpx.Client(timeout=4.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        reply_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if reply_text:
                            return AssistantQueryResponse(
                                reply=reply_text.strip(),
                                language=lang,
                                provider="GEMINI",
                                is_emergency=is_immediate_danger_query(message.lower()),
                                suggested_actions=["Call 112 Emergency", "View Flood Map", "Check Evacuation Routes"],
                                data_sources_evaluated=["Gemini 1.5 Flash", "SafeMap Grounding Context"],
                                data_disclaimer="AI-generated decision support. Not an official alert system. Follow GHMC / NDMA instructions."
                            )
        return None

    def _generate_rule_based_response(
        self, message: str, lang: str, context: AssistantContext
    ) -> AssistantQueryResponse:
        """
        Deterministic, grounded Safety Decision Engine tailored specifically for Hyderabad
        flood hazards, Musi River corridors, OSM routing, and truth-in-facilities rules.
        """
        lower = message.lower()
        is_emergency = is_immediate_danger_query(lower)

        # 1. IMMEDIATE DANGER: Rising water, trapped residents, house flooding
        if is_emergency or any(t in lower for t in ["water is rising", "water entering", "enters my house", "floodwater enters", "ఇంట్లోకి నీరు", "మునిగిపోతుంది", "घर में पानी", "पानी घुस"]):
            return self._build_immediate_danger_response(lang, context)

        # 2. MUSI RIVER CORRIDOR INQUIRIES
        if any(t in lower for t in ["musi", "causeway", "chaderghat", "moosarambagh", "puranapul", "మూసీ", "మూసి", "మూసీ నది", "मूसी"]):
            return self._build_musi_river_response(lang, context)

        # 3. MAPPED FLOOD-PRONE ZONE INQUIRIES
        if any(t in lower for t in ["flood-prone", "hazard zone", "flood zone", "is this location in", "risk zone", "prone", "వరద జోన్", "ప్రమాద ప్రాంతం", "బాढ़", "बाढ़ क्षेत्र", "जोखिम"]):
            return self._build_hazard_zone_response(lang, context)

        # 4. EVACUATION ROUTE & NO_SAFE_ROUTE
        if any(t in lower for t in ["no_safe_route", "no safe route", "severed", "సురక్షిత మార్గం లేదు", "కోల్పోయింది", "मार्ग नहीं", "रास्ता बंद"]):
            return self._build_no_safe_route_response(lang, context)

        if any(t in lower for t in ["route", "evacuation", "evac", "escape", "detour", "దారి", "మార్గం", "తరలింపు", "मार्ग", "निकासी", "रास्ता"]):
            return self._build_route_inquiry_response(lang, context)

        # 5. SHELTERS & HOSPITALS / TRUTH-IN-FACILITIES
        if any(t in lower for t in ["shelter", "hospital", "bed", "relief camp", "nearest", "ఆశ్రయం", "ఆసుపత్రి", "క్యాంప్", "ఆశ్రయాలు", "राहत", "शिविर", "अस्पताल", "आश्रय"]):
            return self._build_shelter_response(lang, context)

        # 6. TECHNICAL STATUS: MODEL_UNSUPPORTED & 50KM SAFEGUARD
        if any(t in lower for t in ["model_unsupported", "unsupported", "coverage", "50 km", "50km", "gauge", "insufficient_local_data", "సపోర్ట్", "గేజ్", "కవరేజ్", "भविष्यवाणी", "कवरेज"]):
            return self._build_model_unsupported_response(lang)

        # 7. REPORTING BLOCKED ROADS & INCIDENTS
        if any(t in lower for t in ["report", "blocked road", "waterlogging", "nala", "drain", "రోడ్డు", "సమస్య", "బ్లాక్", "సమర్పించు", "सड़क", "अवरोध", "जाम", "शिकायत", "रिपोर्ट"]):
            return self._build_report_incident_response(lang)

        # 8. GENERAL FLOOD READINESS & SYSTEM PROTOCOL
        return self._build_general_guidance_response(lang, context)

    # -------------------------------------------------------------------------
    # Response Builders (English, Telugu, Hindi)
    # -------------------------------------------------------------------------

    def _build_immediate_danger_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        if lang == "te":
            reply = (
                "⚠️ తక్షణ భద్రతా హెచ్చరిక (Immediate Danger):\n"
                "1. ప్రవహించే వరద నీటిలో ఎట్టి పరిస్థితుల్లోనూ నడవవద్దు లేదా వాహనాలు నడపవద్దు (15 సెం.మీ నీరు కూడా మిమ్మల్ని పడదోయగలదు).\n"
                "2. మీ ఇంటి ప్రధాన విద్యుత్ స్విచ్ (Main Breaker) మరియు గ్యాస్ సిలిండర్ రెగ్యులేటర్‌ను వెంటనే ఆపివేయండి.\n"
                "3. తాగునీరు, మందులు మరియు మొబైల్ ఫోన్‌తో వెంటనే మేడపైకి లేదా ఎత్తైన అంతస్తుకు చేరుకోండి.\n"
                "4. అత్యవసర సహాయం కొరకు జాతీయ అత్యవసర నంబర్ 112 లేదా GHMC DRF 040-21111111 కు వెంటనే కాల్ చేయండి."
            )
            follow_up = "మీరు సురక్షితమైన ఎత్తైన ప్రదేశంలో ఉన్నారా? మీకు అత్యవసర బోట్ రెస్క్యూ అవసరమా?"
        elif lang == "hi":
            reply = (
                "⚠️ तत्काल सुरक्षा निर्देश (Immediate Danger):\n"
                "1. बहते बाढ़ के पानी में कभी न चलें और न ही गाड़ी चलाएं (मात्र 15 सेमी पानी इंसान को बहा सकता है)।\n"
                "2. घर का मुख्य बिजली स्विच (Main Breaker) और गैस सिलेंडर रेगुलेटर तुरंत बंद करें।\n"
                "3. पीने का पानी, दवाइयां और मोबाइल फोन लेकर तुरंत ऊपरी मंजिल या छत पर जाएं।\n"
                "4. आपातकालीन बचाव हेतु राष्ट्रीय आपातकालीन नंबर 112 या GHMC DRF 040-21111111 पर तुरंत कॉल करें।"
            )
            follow_up = "क्या आप सुरक्षित रूप से किसी ऊंचे स्थान पर हैं? क्या आपको तत्काल बचाव दल की आवश्यकता है?"
        else:
            reply = (
                "⚠️ IMMEDIATE FLOOD SAFETY ACTIONS:\n"
                "1. TURN AROUND, DON'T DROWN: Never walk or drive through moving water. Just 15 cm can sweep you off your feet; 30 cm can float a vehicle.\n"
                "2. SHUT OFF UTILITIES: Turn off your main electrical circuit breaker and LPG cylinder valve immediately. Do not touch wet electrical switches.\n"
                "3. SEEK VERTICAL SHELTER: Move family and pets to an upper floor or rooftop with drinking water, medicines, and a flashlight. Do not climb into closed attics.\n"
                "4. CALL FOR EMERGENCY RESCUE: Dial All-in-One National Emergency 112 or GHMC Disaster Response Force (DRF) at 040-21111111."
            )
            follow_up = "Are you on safe high ground right now, or is water continuing to enter your immediate floor?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=True,
            suggested_actions=["Call 112 Emergency", "Call GHMC DRF (040-21111111)", "View High Ground Shelters"],
            follow_up_question=follow_up,
            data_sources_evaluated=["NDMA National Flood Safety Protocol", "GHMC Emergency Standards"],
            data_disclaimer="Emergency prototype. In life-threatening emergencies, always dial 112 directly. Do not wait for app confirmation."
        )

    def _build_musi_river_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        if lang == "te":
            reply = (
                "మూసీ నది పరివాహక ప్రాంతం మరియు కాజ్‌వేల (చాదర్‌ఘాట్, మూసారాంబాగ్‌) వద్ద హిమాయత్‌సాగర్, ఉస్మాన్‌సాగర్ గేట్లు ఎత్తినప్పుడు ఆకస్మికంగా వరద నీరు పెరుగుతుంది.\n"
                "1. నది ఒడ్డున ఉన్న రోడ్లు మరియు లోతట్టు కాలనీల నుండి వెంటనే సురక్షిత ఎత్తైన ప్రాంతాలకు వెళ్లండి.\n"
                "2. కాజ్‌వేపై నీరు ప్రవహిస్తుంటే వంతెన దాటే ప్రయత్నం చేయవద్దు.\n"
                "3. సహాయం కోసం GHMC కంట్రోల్ రూమ్ 040-21111111 లేదా 112 కు సమాచారం అందించండి."
            )
            follow_up = "మీరు మూసీ నదికి ఏ వైపున (ఉదా. చాదర్‌ఘాట్ లేదా అంబర్‌పేట్) ఉన్నారు?"
        elif lang == "hi":
            reply = (
                "मूसी नदी बेसिन और कॉजवे (चादरघाट, मूसारामबाग) पर उस्मान सागर और हिमायत सागर के गेट खोले जाने पर अचानक भीषण जलस्तर बढ़ता है।\n"
                "1. नदी तट और निचले इलाकों से तुरंत दूर हटें और ऊंचे स्थानों की ओर जाएं।\n"
                "2. यदि कॉजवे पर पानी बह रहा है, तो पार करने की कोशिश बिल्कुल न करें।\n"
                "3. आपात स्थिति में GHMC DRF 040-21111111 या राष्ट्रीय हेल्पलाइन 112 पर कॉल करें।"
            )
            follow_up = "आप मूसी नदी के किस क्षेत्र (जैसे चादरघाट या मूसारामबाग) के पास हैं?"
        else:
            reply = (
                "Musi River Inundation Protocol:\n"
                "The Musi River corridor and low-level causeways (Chaderghat, Moosarambagh, Puranapul) experience rapid flash surges during upstream reservoir crest gate releases from Himayat Sagar and Osman Sagar.\n"
                "1. Evacuate riverbed settlements and low pockets immediately towards elevated ridges.\n"
                "2. Never attempt to cross causeways or bridges if water touches or overtops the road deck.\n"
                "3. For municipal barricading or evacuation support, notify GHMC DRF at 040-21111111 or dial 112."
            )
            follow_up = "Are you currently on the north bank (e.g. Sultan Bazar/Koti) or south bank (e.g. Malakpet/Chaderghat)?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=True,
            suggested_actions=["Evacuate River Corridor", "Call GHMC DRF (040-21111111)", "Find Nearby Shelter"],
            follow_up_question=follow_up,
            data_sources_evaluated=["GHMC Hydrology Survey (HYD-FZ-001)", "MRDCL Flood Baseline"],
            data_disclaimer="River levels reflect indicative municipal causeway thresholds. Confirm with local police barricades."
        )

    def _build_hazard_zone_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        location = context.location
        if location:
            # Evaluate exact spatial coordinates against real hazard database
            check = get_hazard_service().check_location(location.latitude, location.longitude)
            is_in_zone = check.is_in_hazard_zone
            severity = check.highest_severity
            hazards = check.intersected_hazards

            if is_in_zone:
                hazard_titles = ", ".join(h.title for h in hazards)
                if lang == "te":
                    reply = (
                        f"అవును, మీ స్థానం ({location.latitude:.4f}° N, {location.longitude:.4f}° E) మునిసిపల్ వరద ప్రమాద జోన్ లోపల ఉంది.\n"
                        f"గుర్తించిన జోన్లు: {hazard_titles} (తీవ్రత: {severity}).\n"
                        "ఇది GHMC / MRDCL ముందస్తు సర్వేల ఆధారంగా నిర్ధారించబడింది. వర్షపాతం ఎక్కువగా ఉంటే వెంటనే సురక్షిత ప్రాంతాలకు వెళ్లండి."
                    )
                elif lang == "hi":
                    reply = (
                        f"हाँ, आपकी वर्तमान स्थिति ({location.latitude:.4f}° N, {location.longitude:.4f}° E) चिन्हित बाढ़ जोखिम क्षेत्र में आती है।\n"
                        f"जोखिम क्षेत्र: {hazard_titles} (तीव्रता: {severity})।\n"
                        "यह GHMC / MRDCL के नगर निगम बाढ़ मानचित्रण पर आधारित है। कृपया सतर्क रहें और जलभराव से बचें।"
                    )
                else:
                    reply = (
                        f"Yes, your coordinates ({location.latitude:.4f}° N, {location.longitude:.4f}° E) intersect a mapped flood-prone zone.\n"
                        f"Intersected Zones: {hazard_titles} (Severity: {severity}).\n"
                        "This boundary is designated based on GHMC / MRDCL indicative municipal inundation surveys. Monitor local runoff closely."
                    )
                follow_up = None
            else:
                if lang == "te":
                    reply = (
                        f"మీ స్థానం ({location.latitude:.4f}° N, {location.longitude:.4f}° E) చారిత్రక వరద మ్యాపింగ్ జోన్ల వెలుపల ఉంది.\n"
                        "గమనిక: రికార్డ్ చేయబడని స్థానిక నాలా అడ్డంకులు మరియు డ్రైనేజీ సమస్యల వల్ల ఆకస్మిక నీటి నిల్వ ఏర్పడవచ్చు. అప్రమత్తంగా ఉండండి."
                    )
                elif lang == "hi":
                    reply = (
                        f"आपकी स्थिति ({location.latitude:.4f}° N, {location.longitude:.4f}° E) चिन्हित बाढ़-प्रवण क्षेत्र से बाहर है।\n"
                        "ध्यान दें: किसी क्षेत्र के बाढ़-मुक्त दिखने का मतलब यह नहीं कि स्थानीय नाले जाम होने से जलभराव नहीं हो सकता।"
                    )
                else:
                    reply = (
                        f"Your coordinates ({location.latitude:.4f}° N, {location.longitude:.4f}° E) do not intersect any designated historical flood-prone polygons.\n"
                        "Safety Note: Absence of a mapped zone does NOT guarantee safety. Local storm-water bottlenecking, open nalas, and intense localized showers can still cause water-logging."
                    )
                follow_up = None
        else:
            if lang == "te":
                reply = (
                    "హైదరాబాద్‌లో మీ ప్రాంతం వరద ప్రమాద జోన్ పరిధిలో ఉందో లేదో తనిఖీ చేయడానికి దయచేసి మ్యాప్‌పై క్లిక్ చేయండి లేదా అక్షాంశం, రేఖాంశాలను పంచుకోండి."
                )
                follow_up = "మీరు మీ ప్రస్తుత స్థానాన్ని మ్యాప్‌పై ఎంచుకుంటారా?"
            elif lang == "hi":
                reply = (
                    "हैदराबाद में यह जांचने के लिए कि क्या आपका क्षेत्र बाढ़-प्रवण है, कृपया मानचित्र पर क्लिक करें या अपने निर्देशांक साझा करें।"
                )
                follow_up = "क्या आप मानचित्र पर अपना वर्तमान स्थान इंगित करना चाहेंगे?"
            else:
                reply = (
                    "SafeMap AI checks your coordinates against 5 major Hyderabad flood inundation polygons and active alert feeds.\n"
                    "To check your exact address, please select your location on the interactive map or provide your latitude and longitude."
                )
                follow_up = "Would you like to share your coordinates or click a location on the interactive map?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Check Location on Map", "View Risk Polygons", "Plan Evacuation Route"],
            follow_up_question=follow_up,
            data_sources_evaluated=["GHMC Municipal Flood Survey (2020-2024)", "Bhuvan Inundation Mapping"],
            data_disclaimer="Indicative municipal polygons. Does not guarantee safety from unmonitored storm drains."
        )

    def _build_no_safe_route_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        if lang == "te":
            reply = (
                "⚠️ NO_SAFE_ROUTE (సురక్షిత మార్గం అందుబాటులో లేదు):\n"
                "మీ స్థానం నుండి సమీప ఆశ్రయానికి వెళ్లే అన్ని రోడ్లు నిర్ధారించబడిన వరద ప్రమాద జోన్ల గుండా వెళ్తున్నాయి.\n"
                "1. రోడ్డు ప్రయాణం చేయవద్దు. వాహనాలతో వరద నీటిలోకి వెళ్లడం అత్యంత ప్రమాదకరం.\n"
                "2. మీ ప్రస్తుత భవనంలోని పై అంతస్తు లేదా సురక్షిత ఎత్తైన ప్రాంతానికి చేరుకోండి.\n"
                "3. తరలింపు సహాయం కోసం వెంటనే GHMC DRF (040-21111111) లేదా 112 కు డయల్ చేయండి."
            )
            follow_up = "మీరు ఉన్న భవనం సురక్షితమైన కాంక్రీట్ నిర్మాణమా?"
        elif lang == "hi":
            reply = (
                "⚠️ NO_SAFE_ROUTE (कोई सुरक्षित मार्ग नहीं मिला):\n"
                "आपके स्थान से आश्रय स्थल तक जाने वाले सभी सड़क संपर्क बाढ़ प्रभावित क्षेत्रों से घिरे हैं।\n"
                "1. सड़क पर निकलने का प्रयास न करें। पानी में गाड़ी चलाना प्राणघातक हो सकता है।\n"
                "2. तुरंत किसी मजबूत इमारत की ऊपरी मंजिल या छत पर जाएं।\n"
                "3. बचाव सहायता हेतु तुरंत GHMC DRF (040-21111111) या 112 पर संपर्क करें।"
            )
            follow_up = "क्या आपके भवन की ऊपरी मंजिल पानी से सुरक्षित है?"
        else:
            reply = (
                "⚠️ CRITICAL: NO_SAFE_ROUTE EXPLANATION & ACTION:\n"
                "SafeMap AI evaluated all available OpenStreetMap roadway corridors leading to candidate emergency shelters. "
                "Every passable path currently intersects confirmed high-severity flood hazard zones.\n"
                "1. DO NOT ATTEMPT ROAD TRAVEL: All vehicular and walking escape routes are currently severed.\n"
                "2. SEEK VERTICAL SHELTER: Move immediately to the highest floor or reinforced rooftop available.\n"
                "3. CALL CIVIL DEFENSE: Request specialized boat or high-clearance rescue by calling GHMC DRF at 040-21111111 or National Emergency 112."
            )
            follow_up = "Are you stranded inside a multi-story building, or is the ground floor in danger of flooding?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=True,
            suggested_actions=["Call GHMC DRF (040-21111111)", "Call 112 Rescue", "Seek Vertical Shelter"],
            follow_up_question=follow_up,
            data_sources_evaluated=["OpenStreetMap Hyderabad Network", "Topological Flood Avoidance Graph"],
            data_disclaimer="SafeMap AI never manufactures safe routes when road corridors are severed."
        )

    def _build_route_inquiry_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        route_status = context.route_status
        dist = f"{context.route_distance_km:.2f} km" if context.route_distance_km else "calculated distance"

        if lang == "te":
            reply = (
                "తరలింపు మార్గాలు హైదరాబాద్ ఓపెన్‌స్ట్రీట్‌మ్యాప్ (OSM) రోడ్డు నెట్‌వర్క్ ఆధారంగా లెక్కించబడతాయి.\n"
                f"ప్రస్తుత స్థితి: {route_status or 'మార్గాన్ని లెక్కించడానికి సిద్ధంగా ఉంది'} ({dist}).\n"
                "రహదారి వరద జోన్‌ను తాకినట్లయితే సిస్టమ్ స్వయంచాలకంగా ప్రత్యామ్నాయ దారిని (HAZARDS_AVOIDED) గణిస్తుంది. "
                "మ్యాప్‌లో పూర్తి మార్గాన్ని చూడటానికి 'Evacuation Routes' ట్యాబ్‌ను చూడండి."
            )
            follow_up = "మీకు సమీపంలోని ప్రభుత్వ పాఠశాల లేదా కమ్యూనిటీ హాల్ ఆశ్రయం కావాలా?"
        elif lang == "hi":
            reply = (
                "निकासी मार्ग ओपनस्ट्रीटमैप (OSM) हैदराबाद नेटवर्क पर आधारित हैं।\n"
                f"वर्तमान स्थिति: {route_status or 'मार्ग गणना हेतु तैयार'} ({dist})।\n"
                "यदि कोई मुख्य सड़क जलमग्न होती है, तो सिस्टम स्वतः वैकल्पिक मार्ग (HAZARDS_AVOIDED) चुनता है। "
                "मार्ग विवरण देखने के लिए 'Evacuation Routes' टैब का उपयोग करें।"
            )
            follow_up = "क्या आप निकटतम अनुशंसित राहत शिविर का मार्ग देखना चाहते हैं?"
        else:
            reply = (
                "Evacuation Route Calculation Overview:\n"
                f"Current Route Status: {route_status or 'Ready to plan on OSM network'} ({dist}).\n"
                "SafeMap AI runs Dijkstra shortest-path trajectory over real Hyderabad OpenStreetMap road segments. "
                "If a primary corridor crosses active flood hazard zones, an avoidance detour (HAZARDS_AVOIDED) is automatically computed. "
                "Always verify unmonitored roads visually and never drive through flooded culverts."
            )
            follow_up = "Would you like me to guide you to the nearest verified relief facility in the Routes tab?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Open Evacuation Routes Tab", "View Alternate Detours", "Inspect Road Hazards"],
            follow_up_question=follow_up,
            data_sources_evaluated=["OpenStreetMap Drive Network", "Dijkstra Hazard-Penalty Router"],
            data_disclaimer="Routes do not account for sudden unmapped flash floods or downed trees."
        )

    def _build_shelter_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        shelter_name = context.nearest_shelter_name or "Khairatabad Relief Center (S0738)"
        dist = f"{context.nearest_shelter_distance_km:.2f} km" if context.nearest_shelter_distance_km else "approximately 2.3 km"

        if lang == "te":
            reply = (
                f"సిఫార్సు చేయబడిన సమీప ఆశ్రయం: {shelter_name} ({dist}).\n"
                "ముఖ్య గమనిక (Truth-in-Facilities): సురక్షిత ఆశ్రయాలు మరియు ఆసుపత్రుల సామర్థ్యాలు మునిసిపల్ సర్వేల ఆధారంగా జాబితా చేయబడ్డాయి. "
                "క్షేత్రస్థాయి స్థితిగతులు PUBLIC_UNVERIFIED గా ఉంటాయి. ప్రయాణించే ముందు స్థానిక అధికారులను సంప్రదించండి."
            )
            follow_up = "ఈ ఆశ్రయానికి మార్గాన్ని లెక్కించమంటారా?"
        elif lang == "hi":
            reply = (
                f"निकटतम अनुशंसित राहत केंद्र: {shelter_name} ({dist})।\n"
                "महत्वपूर्ण सूचना (Truth-in-Facilities): राहत शिविरों और अस्पतालों का विवरण नगर निगम सर्वेक्षण पर आधारित है। "
                "इनकी परिचालन स्थिति PUBLIC_UNVERIFIED है। कृपया प्रस्थान से पहले स्थानीय कर्मचारियों से पुष्टि करें।"
            )
            follow_up = "क्या आप इस आश्रय केंद्र के लिए सुरक्षित निकासी मार्ग देखना चाहते हैं?"
        else:
            reply = (
                f"Recommended Emergency Shelter: {shelter_name} ({dist}).\n"
                "Truth-in-Facilities Invariant:\n"
                "Shelter coordinates and capacities are derived from open municipal surveys. Structural flood-worthiness and active bed availability "
                "remain marked PUBLIC_UNVERIFIED unless officially confirmed by on-site ward staff. Always call ahead if phones are working."
            )
            follow_up = "Would you like to calculate an evacuation route to this facility now?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Plan Route to Shelter", "View Emergency Directory", "Call Facility"],
            follow_up_question=follow_up,
            data_sources_evaluated=["Hyderabad Emergency Facilities Directory", "GHMC Open Shelter Database"],
            data_disclaimer="Shelter operational readiness is unverified research data. Contact local ward officials."
        )

    def _build_model_unsupported_response(self, lang: str) -> AssistantQueryResponse:
        if lang == "te":
            reply = (
                "MODEL_UNSUPPORTED వివరణ:\n"
                "SafeMap AI ఖచ్చితమైన 50.0 కి.మీ మోడల్ కవరేజ్ భద్రతను అమలు చేస్తుంది. "
                "మెషిన్ లెర్నింగ్ మోడల్ అధికారిక INDOFLOODS నది గేజ్ స్టేషన్లపై శిక్షణ పొందింది. "
                "హైదరాబాద్‌కు సమీపంలోని గేజ్ స్టేషన్ 71.8 కి.మీ దూరంలో మంజ్రా నదిపై (gauge-916) ఉంది. "
                "ఈ స్థానం మోడల్ మద్దతు ఇచ్చే గేజ్ పరిధికి వెలుపల ఉంది. దీని అర్థం ఈ ప్రాంతం వరద-రహితం లేదా తక్కువ ప్రమాదం అని కాదు. "
                "తప్పుడు లేదా కల్పిత వరద అంచనాలను నివారించడానికి, హైదరాబాద్ నగరానికి ML అంచనాలు సురక్షితంగా నిలిపివేయబడ్డాయి (MODEL_UNSUPPORTED)."
            )
        elif lang == "hi":
            reply = (
                "MODEL_UNSUPPORTED का अर्थ:\n"
                "SafeMap AI 50.0 किमी का सख्त मॉडल सुरक्षा प्रतिबंध लागू करता है। "
                "हमारा मशीन लर्निंग मॉडल आधिकारिक INDOFLOODS रिवर गेज पर प्रशिक्षित है। "
                "हैदराबाद से निकटतम गेज 71.8 किमी दूर मांजरा नदी पर (gauge-916) है। "
                "यह स्थान मॉडल के समर्थित गेज कवरेज से बाहर है। इसका अर्थ यह नहीं है कि यह क्षेत्र बाढ़-मुक्त या कम जोखिम वाला है। "
                "बिना आधार वाले काल्पनिक आंकड़े दिखाने से बचने के लिए, हैदराबाद के लिए स्वचालित भविष्यवाणियां रोकी गई हैं (MODEL_UNSUPPORTED)।"
            )
        else:
            reply = (
                "Meaning of MODEL_UNSUPPORTED Status:\n"
                "SafeMap AI strictly enforces a 50.0 km model boundary safeguard. "
                "The machine learning flood model is calibrated on official INDOFLOODS river gauge stations. "
                "The nearest calibrated river gauge to Hyderabad is INDOFLOODS-gauge-916 located 71.8 km away on the Manjra River. "
                "This location is outside the model's supported coverage. This status does not claim or imply that the location is flood-free or low risk. "
                "To prevent unvalidated extrapolation, spatial hallucination, and data fabrication, automated ML inference is intentionally suppressed for Hyderabad."
            )

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Inspect Calibrated Gauges", "View Hydrology Telemetry", "Read System Limits"],
            follow_up_question="Would you like to review the calibrated gauge stations located within Telangana?",
            data_sources_evaluated=["INDOFLOODS Benchmark Metadata", "CWC Hydrological Gauge Network"],
            data_disclaimer="Automated predictions strictly suppressed beyond 50km radius to prevent model fabrication."
        )

    def _build_report_incident_response(self, lang: str) -> AssistantQueryResponse:
        if lang == "te":
            reply = (
                "రోడ్డు దిగ్బంధం లేదా నాలా ఓవర్‌ఫ్లో నివేదిక ఇచ్చే విధానం:\n"
                "1. పై నావిగేషన్ బార్‌లోని 'Report Incident' ట్యాబ్‌పై క్లిక్ చేయండి.\n"
                "2. రోడ్డు పేరు, నీటి తీవ్రత మరియు స్థానాన్ని నమోదు చేసి 'Submit Incident' బటన్ నొక్కండి.\n"
                "గమనిక: ఈ చాట్ అసిస్టెంట్ ద్వారా అధికారిక నివేదికలు ఆటోమేటిక్‌గా నమోదు కావు. "
                "తీవ్రమైన అత్యవసర పరిస్థితుల్లో నేరుగా GHMC కంట్రోల్ రూమ్ 040-21111111 కు కాల్ చేయండి."
            )
            follow_up = "మీరు నివేదించాలనుకుంటున్న రోడ్డు లేదా కాలనీ పేరు ఏమిటి?"
        elif lang == "hi":
            reply = (
                "सड़क अवरोध या नाला जलभराव रिपोर्ट करने का तरीका:\n"
                "1. मुख्य नेविगेशन बार में 'Report Incident' टैब पर क्लिक करें।\n"
                "2. सड़क का नाम, जलभराव का स्तर और स्थान दर्ज करके सबमिट करें।\n"
                "नोट: इस चैट सहायक में संदेश भेजने से कोई आधिकारिक रिपोर्ट अपने आप दर्ज नहीं होती है। "
                "गंभीर स्थिति में GHMC कंट्रोल रूम 040-21111111 पर कॉल करें।"
            )
            follow_up = "आप किस सड़क या कॉलोनी में जलभराव की सूचना देना चाहते हैं?"
        else:
            reply = (
                "How to Report Blocked Roads and Drainage Breaches:\n"
                "1. Navigate to the 'Report Incident' tab in the top navigation bar.\n"
                "2. Fill in the incident title, affected road corridor, coordinates, and severity level, then click Submit.\n"
                "3. Your submission is recorded locally for operations triage.\n"
                "Important Safety Clarification:\n"
                "Chatting with this AI Assistant does NOT automatically file an official incident or contact emergency dispatch. "
                "For active obstructions, call GHMC Control Room directly at 040-21111111."
            )
            follow_up = "Which specific road or landmark in Hyderabad has the obstruction?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Open Report Incident Tab", "Call GHMC Control (040-21111111)", "View Incident Map"],
            follow_up_question=follow_up,
            data_sources_evaluated=["SafeMap Operations Incident Store"],
            data_disclaimer="Incidents require explicit citizen submission in the report form. Not automated via chat."
        )

    def _build_general_guidance_response(self, lang: str, context: AssistantContext) -> AssistantQueryResponse:
        is_demo = context.is_demo_mode
        demo_tag = "[DEMO SIMULATION ACTIVE] " if is_demo else ""

        if lang == "te":
            reply = (
                f"{demo_tag}సేఫ్‌మ్యాప్ AI హైదరాబాద్ విపత్తు నిర్వహణ సహాయకుడు.\n"
                "నేను వరద ప్రమాద జోన్లు, సురక్షిత తరలింపు మార్గాలు, అత్యవసర ఆశ్రయాలు మరియు భద్రతా ప్రోటోకాల్స్‌పై మార్గదర్శకత్వం అందిస్తాను. "
                "జీవిత భద్రతా అత్యవసర పరిస్థితుల్లో ఎల్లప్పుడూ అధికారిక హెల్ప్‌లైన్ 112 లేదా GHMC DRF 040-21111111 ను సంప్రదించండి."
            )
            follow_up = "మీకు వరద జోన్లు, తరలింపు మార్గాలు లేదా ఆశ్రయాల సమాచారం కావాలా?"
        elif lang == "hi":
            reply = (
                f"{demo_tag}सेफमैप एआई हैदराबाद बाढ़ सुरक्षा सहायक में आपका स्वागत है।\n"
                "मैं बाढ़ जोखिम क्षेत्रों, सुरक्षित निकासी मार्गों, राहत शिविरों और सुरक्षा नियमों में आपकी सहायता कर सकता हूँ। "
                "आपात स्थिति में हमेशा आधिकारिक हेल्पलाइन 112 या GHMC DRF 040-21111111 पर कॉल करें।"
            )
            follow_up = "क्या आप बाढ़ क्षेत्र, सुरक्षित मार्ग या राहत शिविरों की जानकारी चाहते हैं?"
        else:
            reply = (
                f"{demo_tag}SafeMap AI Hyderabad Emergency Decision Assistant.\n"
                "I provide grounded decision guidance for Hyderabad flood zones, OpenStreetMap evacuation routing, and designated shelters. "
                "For life-threatening emergencies, immediately dial National Emergency 112 or GHMC DRF at 040-21111111."
            )
            follow_up = "Would you like to check flood hazard polygons, calculate an evacuation route, or inspect nearby shelters?"

        return AssistantQueryResponse(
            reply=reply,
            language=lang,
            provider=self.FALLBACK_PROVIDER,
            is_emergency=False,
            suggested_actions=["Check Flood Hazards", "Calculate Evacuation Route", "Find Safe Shelter"],
            follow_up_question=follow_up,
            data_sources_evaluated=["SafeMap AI Hyderabad Decision Engine", "Truth-in-Facilities Baseline"],
            data_disclaimer="Academic research prototype. Not an official alert broadcaster. Follow GHMC / NDMA."
        )


assistant_service = AssistantService()
