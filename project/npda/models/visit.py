# python imports

# django imports
from django.contrib.gis.db import models

# npda imports
from .help_text_mixin import HelpTextMixin
from .categorised_formfield_mixin import *
from ...constants import (
    ALBUMINURIA_STAGES,
    CLOSED_LOOP_TYPES,
    DKA_ADDITIONAL_THERAPIES,
    GLUCOSE_MONITORING_TYPES,
    HBA1C_FORMATS,
    HOSPITAL_ADMISSION_REASONS,
    RETINAL_SCREENING_RESULTS,
    SMOKING_STATUS,
    THYROID_TREATMENT_STATUS,
    TREATMENT_TYPES,
    YES_NO_UNKNOWN,
)


class Visit(models.Model, HelpTextMixin):
    visit_date = CategorisedDateField(
        verbose_name="Visit/Appointment Date",
        help_text={
            "label": "N.B. the date of any care process or outcome measure within a row may not always be identical to the visit date.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
    )

    height = CategorisedDecimalField(
        verbose_name="Patient Height (cm)",
        help_text={
            "label": "At least one height/weight measurement should be recorded during the audit year. BMI will be calculated centrally.",
            "reference": "NG18: 1.2.45 At each clinic visit for children and young people with type 1 diabetes measure height and weight and plot on an appropriate growth chart. Check for normal growth and/or significant changes in weight because these may reflect changes in blood glucose control. [2004, amended 2015], NG18: 1.3.20 At each clinic visit for children and young people with type 2 diabetes: • measure height and weight and plot on an appropriate growth chart • calculate BMI. Check for normal growth and/or significant changes in weight because these may reflect changes in blood glucose control. [2004, amended 2015]",
        },
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        category="Measurements",
    )

    weight = CategorisedDecimalField(
        verbose_name="Patient Weight (kg)",
        help_text={
            "label": "Patient Weight (kg)",
            "reference": "By providing ALL measurements of HbA1c a more powerful data analysis can be performed centrally. Allows means/median values for the year to be calculated. Data from first 3 months following diagnosis should be supplied but will be analysed independently as early measurements of HbA1c are not representative of overall diabetes control. NG18: 1 1.2.71 Offer children and young people with type 1 diabetes measurement of their HbA1c level 4 times a year (more frequent testing may be appropriate if there is concern about suboptimal blood glucose control). NG18: 1.3.28 Measure HbA1c levels every 3 months in children and young people with type 2 diabetes.",
        },
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        category="Measurements",
    )

    height_weight_observation_date = CategorisedDateField(
        verbose_name="Observation Date (Height and weight)",
        help_text={
            "label": "Combined observation date for height and weight. If only height or weight measured still enter date.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="Measurements",
    )

    hba1c = CategorisedDecimalField(
        verbose_name="Hba1c Value",
        help_text={
            "label": "Collect and submit ALL the measurements with dates taken throughout the audit cycle.",
            "reference": "By providing ALL measurements of HbA1c a more powerful data analysis can be performed centrally. Allows means/median values for the year to be calculated. Data from first 3 months following diagnosis should be supplied but will be analysed independently as early measurements of HbA1c are not representative of overall diabetes control. NG18: 1 1.2.71 Offer children and young people with type 1 diabetes measurement of their HbA1c level 4 times a year (more frequent testing may be appropriate if there is concern about suboptimal blood glucose control). NG18: 1.3.28 Measure HbA1c levels every 3 months in children and young people with type 2 diabetes.",
        },
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        category="HBA1c",
    )

    hba1c_format = CategorisedPositiveSmallIntegerField(
        verbose_name="HbA1c result format",
        help_text={
            "label": "Values in either mmol/mol or % will be accepted.",
            "reference": "",
        },
        choices=HBA1C_FORMATS,
        null=True,
        blank=True,
        default=None,
        category="HBA1c",
    )

    hba1c_date = CategorisedDateField(
        verbose_name="Observation Date: Hba1c Value",
        help_text={
            "label": "Date performed (within the audit year) is mandatory if observation value provided is to be accepted.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="HBA1c",
    )

    treatment = CategorisedPositiveSmallIntegerField(
        verbose_name="Diabetes Treatment at time of Hba1c measurement",
        help_text={
            "label": "Enter the treatment at the time of the visit for all types of diabetes. Options 1-6 usually will relate to children and young people with Type 1 diabetes. Options 7-8 usually will relate to children and young people with non-Type 1 diabetes.",
            "reference": "Important to get information that can relate intensification of insulin regimen to diabetes outcomes.",
        },
        choices=TREATMENT_TYPES,
        null=True,
        blank=True,
        default=None,
        category="Treatment",
    )

    closed_loop_system = CategorisedPositiveSmallIntegerField(
        verbose_name="If treatment included insulin pump therapy (i.e. option 3 or 6 selected), was this part of a closed loop system?",
        help_text={
            "label": "Leave blank if insulin pump not used at time of HbA1c measurement. Licenced closed loop systems currently available in the UK are: • Medtronic 670g & 780g • T:slim Control IQ • CamAPS FX Any others e.g. Omnipod and Dexcom would be DIY, unlicenced.",
            "reference": "Collected for national monitoring of diabetes related technology usage and associated outcomes.",
        },
        choices=CLOSED_LOOP_TYPES,
        null=True,
        blank=True,
        default=None,
        category="Treatment",
    )

    glucose_monitoring = CategorisedPositiveSmallIntegerField(
        verbose_name="At the time of HbA1c measurement, in addition to standard blood glucose monitoring (SBGM), was the patient using any other method of glucose monitoring?",
        help_text={
            "label": "Choose the modified flash glucose monitor option if the patient is using their flash monitor in combination with a separate device or app so that it functions as a continuous glucose monitor, with or without alarms. The Freestyle Libre 2 is classified as a flash glucose monitor.",
            "reference": "Collected for national monitoring of diabetes related technology usage and associated outcomes. NG18: 1.2.62 Offer ongoing real-time continuous glucose monitoring with alarms to children and young people with type 1 diabetes who have: • frequent severe hypoglycaemia or • impaired awareness of hypoglycaemia associated with adverse consequences (for example, seizures or anxiety) or • inability to recognise, or communicate about, symptoms of hypoglycaemia (for example, because of cognitive or neurological disabilities).",
        },
        choices=GLUCOSE_MONITORING_TYPES,
        null=True,
        blank=True,
        default=None,
        category="CGM",
    )

    systolic_blood_pressure = CategorisedIntegerField(
        verbose_name="Systolic Blood Pressure",
        help_text={
            "label": "Mandatory for Blood Pressure care process completion. Enter Systolic BP and Diastolic BP (if collected) Please use the methodology from the Diagnosis, Evaluation, and Treatment of High Blood Pressure in Children and Adolescents Report if performed.",
            "reference": "To assess cardiovascular risk. NG18: 1.2.110 Offer children and young people with type 1 diabetes monitoring for: hypertension annually from 12 years. NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for: hypertension starting at diagnosis.",
        },
        null=True,
        blank=True,
        default=None,
        category="BP",
    )

    diastolic_blood_pressure = CategorisedIntegerField(
        verbose_name="Diastolic Blood pressure",
        help_text={
            "label": "Mandatory for Blood Pressure care process completion. Enter Systolic BP and Diastolic BP (if collected) Please use the methodology from the Diagnosis, Evaluation, and Treatment of High Blood Pressure in Children and Adolescents Report if performed.",
            "reference": "To assess cardiovascular risk. NG18: 1.2.110 Offer children and young people with type 1 diabetes monitoring for: hypertension annually from 12 years. NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for: hypertension starting at diagnosis.",
        },
        null=True,
        blank=True,
        default=None,
        category="BP",
    )

    blood_pressure_observation_date = CategorisedDateField(
        verbose_name="Observation Date (Blood Pressure)",
        help_text={
            "label": "Provide an observation date within the audit period. Date relates to both the systolic AND/OR diastolic pressure measurement.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="BP",
    )

    foot_examination_observation_date = CategorisedDateField(
        verbose_name="Foot Assessment / Examination Date",
        help_text={
            "label": "Complete only if screen performed. Mandatory care process if 12 years or older.",
            "reference": "NG19: 1.3.2 For young people with diabetes who are 12–17 years, the paediatric care team or the transitional care team should assess the young person's feet as part of their annual assessment, and provide information about foot care. If a diabetic foot problem is found or suspected, the paediatric care team or the transitional care team should refer the young person to an appropriate specialist.",
        },
        null=True,
        blank=True,
        default=None,
        category="Foot Care",
    )

    retinal_screening_observation_date = CategorisedDateField(
        verbose_name="Retinal Screening date",
        help_text={
            "label": "Complete only if screen performed. Mandatory care process if 12 years or older",
            "reference": "NG18: 1.2.110 Offer children and young people with type 1 diabetes monitoring for: • diabetic retinopathy annually from 12 years NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for: • diabetic retinopathy from 12 years",
        },
        null=True,
        blank=True,
        default=None,
        category="DECS",
    )

    retinal_screening_result = CategorisedPositiveSmallIntegerField(
        verbose_name="Retinal Screening Result",
        help_text={
            "label": "Provide a result for retinal screening only if screen performed. Abnormal is defined as any level of retinopathy in either eye.",
            "reference": "",
        },
        choices=RETINAL_SCREENING_RESULTS,
        null=True,
        blank=True,
        default=None,
        category="DECS",
    )

    albumin_creatinine_ratio = CategorisedDecimalField(
        verbose_name="Urinary Albumin Level (ACR)",
        help_text={
            "label": "Mandatory for children with type 1 diabetes aged 12 years and above and optional before 12 years. Mandatory for children with type 2 diabetes from diagnosis.",
            "reference": "Albuminuria is a marker for future microvascular complications and early mortality but is rare during prepuberty. Its presence requires intensification of both monitoring and diabetes therapy which can result in lower albuminuria levels and reduced risk of future complications. NG18: 1.2.110 Offer children and young people with type 1 diabetes monitoring for moderately increased albuminuria (albumin:creatinine ratio [ACR] 3–30 mg/mmol; 'microalbuminuria') to detect diabetic kidney disease, annually from 12 years . NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for moderately increased albuminuria (albumin:creatinine ratio [ACR] 3–30 mg/mmol; 'microalbuminuria') to detect diabetic kidney disease, starting at diagnosis. Necessary to determine national prevalence of albuminuria.",
        },
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        category="ACR",
    )

    albumin_creatinine_ratio_date = CategorisedDateField(
        verbose_name="Observation Date: Urinary Albumin Level",
        help_text={
            "label": "Provide and observation date if a value provided.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="ACR",
    )

    albuminuria_stage = CategorisedPositiveSmallIntegerField(
        verbose_name="Albuminuria Stage",
        help_text={
            "label": "Submit your interpretation of the urinary albumin level based on your local laboratory reference ranges. Mandatory if level submitted.",
            "reference": "Albuminuria is a marker for future microvascular complications and early mortality but is rare during prepuberty. Its presence requires intensification of both monitoring and diabetes therapy which can result in lower albuminuria levels and reduced risk of future complications. NG18: 1.2.110 Offer children and young people with type 1 diabetes monitoring for moderately increased albuminuria (albumin:creatinine ratio [ACR] 3–30 mg/mmol; 'microalbuminuria') to detect diabetic kidney disease, annually from 12 years . NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for moderately increased albuminuria (albumin:creatinine ratio [ACR] 3–30 mg/mmol; 'microalbuminuria') to detect diabetic kidney disease, starting at diagnosis. Necessary to determine national prevalence of albuminuria.",
        },
        choices=ALBUMINURIA_STAGES,
        null=True,
        blank=True,
        default=None,
        category="ACR",
    )

    total_cholesterol = CategorisedDecimalField(
        verbose_name="Total Cholesterol Level (mmol/l)",
        help_text={
            "label": "Mandatory only for children with type 2 diabetes annually from diagnosis. Entry for patient with type 1 s is optional and will not be included as an essential care process but will be reported as an outcome measure. Report if performed.",
            "reference": "NG18: 1.3.43 Offer children and young people with type 2 diabetes annual monitoring for dyslipidaemia starting at diagnosis.",
        },
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        category="Cholesterol",
    )

    total_cholesterol_date = CategorisedDateField(
        verbose_name="Observation Date: Total Cholesterol Level",
        help_text={
            "label": "Mandatory to provide an observation date if performed.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="Cholesterol",
    )

    thyroid_function_date = CategorisedDateField(
        verbose_name="Observation Date: Thyroid Function",
        help_text={
            "label": "Mandatory if thyroid testing performed, Data for this item can be entered into the audit if prescribed at a video/telephone appointment",
            "reference": "Thyroid treatment allows prevalence of thyroid autoimmunity associated with Type 1 diabetes to be calculated.",
        },
        null=True,
        blank=True,
        default=None,
        category="Thyroid",
    )

    thyroid_treatment_status = CategorisedPositiveSmallIntegerField(
        verbose_name="At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
        help_text={
            "label": "Mandatory if thyroid testing performed, Data for this item can be entered into the audit if prescribed at a video/telephone appointment",
            "reference": "Thyroid treatment allows prevalence of thyroid autoimmunity associated with Type 1 diabetes to be calculated.",
        },
        choices=THYROID_TREATMENT_STATUS,
        null=True,
        blank=True,
        default=None,
        category="Thyroid",
    )

    coeliac_screen_date = CategorisedDateField(
        verbose_name="Observation Date: Coeliac Disease Screening",
        help_text={
            "label": "Date of coeliac disease screening only to be completed if patient was diagnosed within audit year. Process complete if date is within 90 days of diagnosis for patient with Type 1 diabetes.",
            "reference": "NG 20: 1.1.1 Offer serological testing for coeliac disease to people with: Type 1 diabetes, at diagnosis.",
        },
        null=True,
        blank=True,
        default=None,
        category="Coeliac",
    )

    gluten_free_diet = CategorisedPositiveSmallIntegerField(
        verbose_name="Has the patient been recommended a Gluten-free diet?",
        help_text={
            "label": "Provide dietary status for all patients: A 'yes' response will be interpreted as the patient having a diagnosis of coeliac disease. Dietary status should be reported for every patient within each audit year to allow prevalence of coeliac disease to be calculated. Data for this item can be entered into the audit if a gluten-free diet was recommended at a video/telephone appointment.",
            "reference": "NG 20: 1.1.1 Offer serological testing for coeliac disease to people with: Type 1 diabetes, at diagnosis.",
        },
        choices=YES_NO_UNKNOWN,
        null=True,
        blank=True,
        default=None,
        category="Coeliac",
    )

    psychological_screening_assessment_date = CategorisedDateField(
        verbose_name="Observation Date - Psychological Screening Assessment",
        help_text={
            "label": "The absence of a date will be taken to indicate assessment for need of psychological support outside of MDT clinics has not taken place. Data for this item can be entered into the audit if an assessment was performed remotely e.g. via video/telephone.",
            "reference": "Regular assessment of a broad range of psychological and behavioural problems in children and adults with type 1 diabetes is recommended. SIGN Guideline 16: In children this should include eating disorders, behavioural, emotional and family functioning problems (Management of diabetes, p5). NG18: 1.2.94. Diabetes teams should be aware that children and young people with type 1 diabetes have a greater risk of emotional and behavioural difficulties. [2004, amended 2015] NG18: 1.2.95 Offer children and young people with type 1 diabetes and their family members or carers (as appropriate) emotional support after diagnosis, which should be tailored to their emotional, social, cultural and age-dependent needs. [2004] NG18: 1.2.96 Assess the emotional and psychological wellbeing of young people with type 1 diabetes who present with frequent episodes of diabetic ketoacidosis (DKA). [2004, amended 2015] NG18: 1.2.97 Be aware that a lack of adequate psychosocial support has a negative effect on various outcomes, including blood glucose control in children and young people with type 1 diabetes, and that it can also reduce their self-esteem. [2004, amended 2015] NG18: 1.2.98 Offer children and young people with type 1 diabetes and their family members or carers (as appropriate) timely and ongoing access to mental health professionals with an understanding of diabetes because they may experience psychological problems (such as anxiety, depression, behavioural and conduct disorders and family conflict) or psychosocial difficulties that can impact on the management of diabetes and wellbeing. [2004, amended 2015]",
        },
        null=True,
        blank=True,
        default=None,
        category="Psychology",
    )

    psychological_additional_support_status = CategorisedPositiveSmallIntegerField(
        verbose_name="Was the patient assessed as requiring additional psychological/CAMHS support outside of MDT clinics?",
        help_text={
            "label": "Applicable if patient was assessed to require ongoing psychological/CAMHS support. If the patient is already receiving treatment, record ‘Yes’. Data for this item can be entered into the audit if determined following a remote assessment. NG18: 1.3.37 Offer children and young people with type 2 diabetes and their family members or carers (as appropriate) timely and ongoing access to mental health professionals with an understanding of diabetes because they may experience psychological problems (such as anxiety, depression, behavioural and conduct disorders and family conflict) or psychosocial difficulties that can impact on the management of diabetes and wellbeing. [2004, amended 2015]",
            "reference": "",
        },
        choices=YES_NO_UNKNOWN,
        null=True,
        blank=True,
        default=None,
        category="Psychology",
    )

    smoking_status = CategorisedPositiveSmallIntegerField(
        verbose_name="Does the patient smoke?",
        help_text={
            "label": "Enter smoking status of the patient. Data for this item can be entered into the audit if collected at a video/telephone appointment.",
            "reference": "Smoking plays a significant contribution to micro and macrovascular disease development. Important to ascertain prevalence of smoking amongst the diabetic population.",
        },
        choices=SMOKING_STATUS,
        null=True,
        blank=True,
        default=None,
        category="Smoking",
    )

    smoking_cessation_referral_date = CategorisedDateField(
        verbose_name="Date of offer of referral to smoking cessation service (if patient is a current smoker)",
        help_text={
            "label": "Leave blank if not made. Data for this item can be entered into the audit if offered at a video/telephone appointment.",
            "reference": "NG18: 1.2.14 Offer smoking cessation programmes to children and young people with type 1 diabetes who smoke. See also the NICE guidelines on brief interventions and referral for smoking cessation, smoking cessation services, harm reduction approaches to smoking, and smoking cessation in secondary care. [2004, amended 2015] NG18: 1.3.10 Offer smoking cessation programmes to children and young people with type 2 diabetes who smoke. See also the NICE guidelines on brief interventions and referral for smoking cessation, smoking cessation services, harm reduction approaches to smoking, and smoking cessation in secondary care. [2004, amended 2015]",
        },
        null=True,
        blank=True,
        default=None,
        category="Smoking",
    )

    carbohydrate_counting_level_three_education_date = CategorisedDateField(
        verbose_name="Date of Level 3 carbohydrate counting education received",
        help_text={
            "label": "Level 3 carbohydrate counting is defined as carbohydrate counting with adjustment of insulin dosage according to an insulin:carbohydrate ratio. Enter date when provided. Process complete if date is within 14 days of diagnosis for patient with Type 1 diabetes. To be reported for patients diagnosed with type 1 diabetes during the audit year. If no date entered during the audit year then an assumption of incomplete care process will be made. Data for this item can be entered into the audit if received at a video/telephone appointment.",
            "reference": "NG18: 1.2.37 Offer level 3 carbohydrate-counting education from diagnosis to children and young people with type 1 diabetes who are using a multiple daily insulin injection regimen or continuous subcutaneous insulin infusion (CSII or insulin pump) therapy, and to their family members or carers (as appropriate), and repeat the offer at intervals thereafter. Will be reported for patients diagnosed within audit year.",
        },
        null=True,
        blank=True,
        default=None,
        category="Dietician",
    )

    dietician_additional_appointment_offered = CategorisedPositiveSmallIntegerField(
        verbose_name="Was the patient offered an additional appointment with a paediatric dietitian?",
        help_text={
            "label": "The additional appointment could be 1:1 or group session, via phone call, video call or face to face.",
            "reference": "BPT indicator: Each patient should be offered at least one additional appointment per year with a paediatric dietitian (outside of the MDT clinic) with training in diabetes (or equivalent appropriate experience)",
        },
        choices=YES_NO_UNKNOWN,
        null=True,
        blank=True,
        default=None,
        category="Dietician",
    )

    dietician_additional_appointment_date = CategorisedDateField(
        verbose_name="Date of additional appointment with dietitian",
        help_text={"label": "", "reference": ""},
        null=True,
        blank=True,
        default=None,
        category="Dietician",
    )

    flu_immunisation_recommended_date = CategorisedDateField(
        verbose_name="Date that influenza immunisation was recommended",
        help_text={
            "label": "If no date entered during the audit year then an assumption of incomplete care process will be made. Data for this item can be entered into the audit if the influenza immunisation was recommended at a video/telephone appointment.",
            "reference": "NG18: 1.2.16 Explain to children and young people with type 1 diabetes and their family members or carers (as appropriate) that the Department of Health's Green Book recommends annual immunisation against influenza for children and young people with diabetes over the age of 6months. [2004] NG18: 1.3.12 Explain to children and young people with type 2 diabetes and their family members or carers (as appropriate) that the Department of Health's Green Book recommends annual immunisation against influenza for children and young people with diabetes. [2004, amended 2015]",
        },
        null=True,
        blank=True,
        default=None,
        category="Immunisation (flu)",
    )

    ketone_meter_training = CategorisedPositiveSmallIntegerField(
        verbose_name="Was the patient using (or trained to use) blood ketone testing equipment at time of visit?",
        help_text={
            "label": "Type 1 diabetes only Data for this item can be entered into the audit if collected at a video/telephone appointment.",
            "reference": "NG18: 1.2.74 Offer children and young people with type 1 diabetes blood ketone testing strips and a meter, and advise them and their family members or carers (as appropriate) to test for ketonaemia if they are ill or have hyperglycaemia.",
        },
        choices=YES_NO_UNKNOWN,
        null=True,
        blank=True,
        default=None,
        category="Sick Day Rules",
    )

    sick_day_rules_training_date = CategorisedDateField(
        verbose_name="Date of provision of advice ('sick-day rules') about managing diabetes during intercurrent illness or episodes of hyperglycaemia",
        help_text={
            "label": "Applies to patients with type 1 and type 2 diabetes. If no date entered during the audit year then an assumption of incomplete care process will be made. Data for this item can be entered into the audit if given at a video/telephone appointment.",
            "reference": "NG18: 1.2.73 Provide each child and young person with type 1 diabetes and their family members or carers (as appropriate) with clear individualised oral and written advice ('sick-day rules') about managing type 1 diabetes during inter-current illness or episodes of hyperglycaemia, including: • monitoring blood glucose • monitoring and interpreting blood ketones (betahydroxybutyrate) • adjusting their insulin regimen, food and fluid intake • when and where to seek further advice or help. Revisit the advice with the child or young person and their family members or carers, (as appropriate) at least annually. NG18: 1.3.1 Offer children and young people with type 2 diabetes and their family members or carers (as appropriate) a continuing programme of education from diagnosis. Ensure that the programme includes the following core topics: • HbA1c monitoring and targets • the effects of inter-current illness on blood glucose control • the aims of metformin therapy and possible adverse effects • the complications of type 2 diabetes and how to prevent them .",
        },
        null=True,
        blank=True,
        default=None,
        category="Sick Day Rules",
    )

    hospital_admission_date = CategorisedDateField(
        verbose_name="Start date (Hospital Provider Spell)",
        help_text={
            "label": "Please enter every hospital admission the patient has had (day case or longer) on separate rows. These should include admissions for stabilisation of diabetes (at diagnosis and/or in established patients), DKA (new and/or established patients), ketosis without acidosis, hypoglycaemia, surgical procedures or other causes.",
            "reference": "",
        },
        null=True,
        blank=True,
        default=None,
        category="Hospital Admission",
    )

    hospital_discharge_date = CategorisedDateField(
        verbose_name="Discharge date (Hospital provider spell)",
        help_text={"label": "", "reference": "For calculating number of bed days."},
        null=True,
        blank=True,
        default=None,
        category="Hospital Admission",
    )

    hospital_admission_reason = CategorisedPositiveSmallIntegerField(
        verbose_name="Use option 1: Stabilisation of diabetes for new patients admitted without DKA or other admissions where the purpose was to stabilise blood glucose such as recurrent hyperglycaemia without acidosis.",
        help_text={
            "label": "",
            "reference": "Important to know why a child is admitted to hospital for reasons of having diabetes but not related to DKA or hypoglycaemia. Also to record incidence of DKA and hypoglycaemia complications. With Best Practice Tariff it is envisaged that this type of admission will decrease and this is of interest to commissioners. Please only record diabetes-related admissions.",
        },
        choices=HOSPITAL_ADMISSION_REASONS,
        null=True,
        blank=True,
        default=None,
        category="Hospital Admission",
    )

    dka_additional_therapies = CategorisedPositiveSmallIntegerField(
        verbose_name="Additional therapies used in DKA management",
        help_text={
            "label": "Only complete if DKA selected in previous question: During this DKA admission did the patient receive any of the following therapies?",
            "reference": "",
        },
        choices=DKA_ADDITIONAL_THERAPIES,
        null=True,
        blank=True,
        default=None,
        category="Hospital Admission",
    )

    hospital_admission_other = CategorisedCharField(
        verbose_name="Only complete if OTHER selected: Reason for admission (free text)",
        help_text={
            "label": "Mandatory only if ‘Other causes' selected as Reason for admission.",
            "reference": "",
        },
        max_length=500,
        null=True,
        blank=True,
        default=None,
        category="Hospital Admission",
    )

    is_valid = models.BooleanField(
        verbose_name="Record is valid", blank=True, null=True, default=False
    )

    errors = models.JSONField(
        verbose_name="Validation errors", blank=True, null=True, default=None
    )

    # relationships

    patient = models.ForeignKey(to="npda.Patient", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Visit"
        verbose_name_plural = "Visits"
        ordering = ("-visit_date",)

    def __str__(self) -> str:
        return f"Patient visit for {self.patient} on {self.visit_date}"
