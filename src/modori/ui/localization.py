from __future__ import annotations

from collections.abc import Mapping
import re


UI_MESSAGE_EN: Mapping[str, str] = {
    "지원하지 않는 모드입니다.": "This mode is not supported.",
    "모드가 변경되었습니다.": "The mode was changed.",
    "패치 종류가 필요합니다.": "A patch type is required.",
    "단계가 변경되었습니다.": "The step was updated.",
    "최근 파일을 찾을 수 없습니다.": "The recent file could not be found.",
    "다시 실행할 분석이 없습니다.": "There is no analysis to run again.",
    "다시 실행을 시작했습니다.": "The analysis started again.",
    "분석 결과가 업데이트되었습니다.": "The analysis results were updated.",
    "분석 후보를 찾을 수 없습니다.": "The analysis candidate could not be found.",
    "검토할 분석 후보를 선택했습니다.": "The analysis candidate was selected for review.",
    "분석 설정을 확정했습니다. 실행 버튼을 눌러야 계산이 시작됩니다.": (
        "The analysis settings were confirmed. Select Run to start the calculation."
    ),
    "새 데이터 파일을 열면 현재 분석 단계가 초기화됩니다.": (
        "Opening a new data file will reset the current analysis steps."
    ),
    "데이터 파일을 가져오지 못했습니다.": "The data file could not be imported.",
    "데이터 파일을 가져왔습니다.": "The data file was imported.",
    "분석 단계를 수정하지 못했습니다.": "The analysis step could not be updated.",
    "엔진 실행 중 오류가 발생했습니다.": "An error occurred while running the engine.",
    "분석 결과를 표시할 수 없습니다.": "The analysis results cannot be displayed.",
    "수정할 데이터가 없습니다.": "There is no data to edit.",
    "변수를 찾을 수 없습니다.": "The variable could not be found.",
    "지원하지 않는 측정수준입니다.": "This measure level is not supported.",
    "변수 메타데이터를 수정하지 못했습니다.": "The variable metadata could not be updated.",
    "변수 메타데이터가 변경되었습니다.": "The variable metadata was updated.",
    "내보낼 분석 결과가 없습니다.": "There are no analysis results to export.",
    "보고서를 내보내지 못했습니다.": "The report could not be exported.",
    "보고서 파일이 생성되지 않았습니다.": "The report file was not created.",
    "보고서에 선택 경로 안내를 기록하지 못했습니다.": (
        "The selection-path note could not be written to the report."
    ),
    "보고서 저장 경로를 확인하지 못했습니다.": (
        "The report destination could not be verified."
    ),
    "기존 보고서를 안전하게 보관하지 못했습니다.": (
        "The existing report could not be preserved safely."
    ),
    "기존 보고서를 자동으로 복구하지 못했습니다. 원래 보고서 폴더의 보관 파일을 확인해 주세요.": (
        "The existing report could not be restored automatically. "
        "Check the backup file in the original report folder."
    ),
    "같은 이름의 보고서가 이미 있습니다. 기존 파일을 바꿀지 확인해 주세요.": (
        "A report with this name already exists. Confirm whether to replace it."
    ),
    "보고서를 내보냈습니다.": "The report was exported.",
    "설명 항목을 찾을 수 없습니다.": "The explanation entry could not be found.",
    "지원하지 않는 파일 형식입니다.": "This file type is not supported.",
    "파일 미리보기를 만들지 못했습니다.": "The file preview could not be created.",
    "가져올 파일이 선택되지 않았습니다.": "No file was selected for import.",
    "첫 번째 행을 헤더로 인식했습니다.": (
        "The first row was recognized as the header."
    ),
    "표 데이터가 없습니다. 원본 포털에서 CSV 파일을 다시 받거나 표가 있는 시트를 선택해 주세요.": (
        "No table data was found. Download the CSV again from the source portal or select a sheet that contains a table."
    ),
    "변환 단계가 추가되었습니다. 다시 실행하면 결과가 업데이트됩니다.": (
        "The transformation step was added. Run the analysis again to update the results."
    ),
    "결측 처리 기준을 확인해 주세요.": "Review the missing-value handling rule.",
    "결측 코드는 숫자 목록이어야 합니다.": "Missing-value codes must be a list of numbers.",
    "변경할 속성이 없습니다.": "There are no properties to update.",
    "통일할 값 제안이 없습니다.": "There are no value-unification suggestions.",
    "값 수정 규칙은 기존값=새값 형식이어야 합니다.": (
        "Value-editing rules must use the old=value format."
    ),
    "변경된 데이터 구성을 다시 확인하거나 분석 방법을 직접 구성해 주세요.": (
        "Review the changed data configuration or configure the analysis directly."
    ),
    "변경된 데이터 구성을 다시 확인한 뒤 보고서를 저장해 주세요.": (
        "Review the changed data configuration before saving the report."
    ),
    "자동 그래프를 생성하지 못했습니다.": "The automatic chart could not be created.",
    "실행할 분석이 없습니다. 분석 방법을 선택하고 변수를 지정해 주세요.": (
        "There is no analysis to run. Choose an analysis method and assign its variables."
    ),
    "변환할 데이터가 없습니다.": "There is no data to transform.",
    "변환 단계를 추가하지 못했습니다.": "The transformation step could not be added.",
    "역코딩 설정을 확인해 주세요.": "Review the reverse-coding settings.",
    "척도 점수 설정을 확인해 주세요.": "Review the scale-score settings.",
    "값 통일 설정을 확인해 주세요.": "Review the value-unification settings.",
    "값 수정 설정을 확인해 주세요.": "Review the value-editing settings.",
    "새 변수명이 기존 변수와 충돌합니다.": (
        "The new variable name conflicts with an existing variable."
    ),
    "패치는 객체여야 합니다.": "The patch must be an object.",
    "서로 다른 두 집단을 선택해야 합니다.": "Select two different groups.",
    "측정수준은 scale, ordinal, nominal 중 하나여야 합니다.": (
        "The measure level must be scale, ordinal, or nominal."
    ),
    "display_type 메타데이터 변경은 아직 지원하지 않습니다.": (
        "Changing display_type metadata is not supported yet."
    ),
    "missing_codes와 missing_values를 동시에 보낼 수 없습니다.": (
        "missing_codes and missing_values cannot be provided together."
    ),
    "missing_codes 필드는 목록이어야 합니다.": (
        "The missing_codes field must be a list."
    ),
    "new_value 필드가 필요합니다.": "The new_value field is required.",
    "기술통계 표에는 하나 이상의 변수가 필요합니다.": (
        "Descriptives Table 1 requires at least one variable."
    ),
    "기술통계 변수에 중복이 있습니다.": (
        "The descriptive variables contain duplicates."
    ),
    "그룹 변수는 기술통계 변수와 달라야 합니다.": (
        "The group variable must differ from the descriptive variables."
    ),
    "그룹 변수는 비어 있지 않은 문자열이어야 합니다.": (
        "The group variable must be a non-empty string."
    ),
    "기술통계 표 파라미터 schema_version이 필요합니다.": (
        "Descriptives Table 1 requires a schema_version parameter."
    ),
    "기술통계 표 변수가 변경되었습니다.": (
        "The Descriptives Table 1 variables were updated."
    ),
    "신뢰도 분석에는 문항 변수가 필요합니다.": (
        "Reliability analysis requires item variables."
    ),
    "신뢰도 분석에는 세 개 이상의 문항 변수가 필요합니다.": (
        "Reliability analysis requires at least three item variables."
    ),
    "신뢰도 문항 변수에 중복이 있습니다.": (
        "The reliability item variables contain duplicates."
    ),
    "신뢰도 분석 변수가 변경되었습니다.": (
        "The reliability-analysis variables were updated."
    ),
    "결과 변수와 집단 변수를 모두 입력해야 합니다.": (
        "Enter both an outcome variable and a group variable."
    ),
    "집단 비교에는 결과 변수와 집단 변수가 모두 필요합니다.": (
        "Group comparison requires both an outcome variable and a group variable."
    ),
    "결과 변수와 집단 변수는 달라야 합니다.": (
        "The outcome and group variables must differ."
    ),
    "집단 비교 변수가 변경되었습니다.": (
        "The group-comparison variables were updated."
    ),
    "대응표본 비교에는 사전 변수와 사후 변수가 모두 필요합니다.": (
        "Paired comparison requires both pre and post variables."
    ),
    "사전 변수와 사후 변수는 달라야 합니다.": (
        "The pre and post variables must differ."
    ),
    "종속 변수와 예측 변수를 모두 입력해야 합니다.": (
        "Enter both a dependent variable and predictor variables."
    ),
    "회귀분석에는 종속 변수와 예측 변수가 모두 필요합니다.": (
        "Regression requires both a dependent variable and predictor variables."
    ),
    "회귀분석 예측 변수에 중복이 있습니다.": (
        "The regression predictors contain duplicates."
    ),
    "종속 변수는 예측 변수에 포함될 수 없습니다.": (
        "The dependent variable cannot also be a predictor."
    ),
    "회귀분석 변수가 변경되었습니다.": "The regression variables were updated.",
    "빈도분석에는 하나 이상의 변수가 필요합니다.": (
        "Frequency analysis requires at least one variable."
    ),
    "빈도분석 변수에 중복이 있습니다.": (
        "The frequency-analysis variables contain duplicates."
    ),
    "빈도분석 파라미터 schema_version이 필요합니다.": (
        "Frequency analysis requires a schema_version parameter."
    ),
    "빈도분석 변수가 변경되었습니다.": (
        "The frequency-analysis variables were updated."
    ),
    "교차분석에는 행 변수와 열 변수가 모두 필요합니다.": (
        "Crosstab analysis requires both a row variable and a column variable."
    ),
    "교차분석의 행 변수와 열 변수는 달라야 합니다.": (
        "The crosstab row and column variables must differ."
    ),
    "빈도 및 교차분석 mode는 frequency 또는 crosstab이어야 합니다.": (
        "The frequency/crosstab mode must be frequency or crosstab."
    ),
    "상관분석에는 두 개 이상의 변수가 필요합니다.": (
        "Correlation analysis requires at least two variables."
    ),
    "상관분석 변수에 중복이 있습니다.": (
        "The correlation variables contain duplicates."
    ),
    "상관분석 파라미터 schema_version이 필요합니다.": (
        "Correlation analysis requires a schema_version parameter."
    ),
    "상관분석 변수가 변경되었습니다.": (
        "The correlation variables were updated."
    ),
    "상관분석 설정이 올바르지 않습니다.": (
        "The correlation-analysis configuration is invalid."
    ),
    "일원분산분석에는 종속 변수와 집단 변수가 모두 필요합니다.": (
        "One-way ANOVA requires both a dependent variable and a group variable."
    ),
    "일원분산분석 파라미터 schema_version이 필요합니다.": (
        "One-way ANOVA requires a schema_version parameter."
    ),
    "일원분산분석 변수가 변경되었습니다.": (
        "The one-way ANOVA variables were updated."
    ),
    "종속 변수와 집단 변수는 달라야 합니다.": (
        "The dependent and group variables must differ."
    ),
    "Kruskal-Wallis 검정에는 종속 변수와 집단 변수가 모두 필요합니다.": (
        "The Kruskal–Wallis test requires both a dependent variable and a group variable."
    ),
    "Kruskal-Wallis 파라미터 schema_version이 필요합니다.": (
        "The Kruskal–Wallis test requires a schema_version parameter."
    ),
    "Kruskal-Wallis 검정 변수가 변경되었습니다.": (
        "The Kruskal–Wallis variables were updated."
    ),
    "ANCOVA에는 종속 변수, 집단 변수, 공변량이 모두 필요합니다.": (
        "ANCOVA requires a dependent variable, a group variable, and covariates."
    ),
    "ANCOVA 변수에는 중복이 있을 수 없습니다.": (
        "ANCOVA variables cannot contain duplicates."
    ),
    "ANCOVA 파라미터 schema_version이 필요합니다.": (
        "ANCOVA requires a schema_version parameter."
    ),
    "ANCOVA 변수가 변경되었습니다.": "The ANCOVA variables were updated.",
    "요인/PCA 분석에는 세 개 이상의 변수가 필요합니다.": (
        "Factor/PCA analysis requires at least three variables."
    ),
    "요인/PCA 변수에 중복이 있습니다.": (
        "The Factor/PCA variables contain duplicates."
    ),
    "요인/PCA 파라미터 schema_version이 필요합니다.": (
        "Factor/PCA analysis requires a schema_version parameter."
    ),
    "요인/PCA 분석 변수가 변경되었습니다.": (
        "The Factor/PCA variables were updated."
    ),
    "반복측정 분석에는 세 개 이상의 변수가 필요합니다.": (
        "Repeated-measures analysis requires at least three variables."
    ),
    "반복측정 분산분석에는 세 개 이상의 반복 측정 변수가 필요합니다.": (
        "Repeated-measures ANOVA requires at least three repeated variables."
    ),
    "반복측정 변수에 중복이 있습니다.": (
        "The repeated-measures variables contain duplicates."
    ),
    "반복측정 분석 파라미터 schema_version이 필요합니다.": (
        "Repeated-measures analysis requires a schema_version parameter."
    ),
    "반복측정 분산분석 변수가 변경되었습니다.": (
        "The repeated-measures ANOVA variables were updated."
    ),
    "Friedman 검정에는 세 개 이상의 반복 측정 변수가 필요합니다.": (
        "The Friedman test requires at least three repeated variables."
    ),
    "Friedman 반복 측정 변수에 중복이 있습니다.": (
        "The Friedman repeated variables contain duplicates."
    ),
    "Friedman 검정 변수가 변경되었습니다.": (
        "The Friedman-test variables were updated."
    ),
    "매개분석에는 X, 매개변수, 결과 변수가 모두 필요합니다.": (
        "Mediation analysis requires X, a mediator, and an outcome variable."
    ),
    "매개분석 변수에는 중복이 있을 수 없습니다.": (
        "Mediation variables cannot contain duplicates."
    ),
    "매개분석 파라미터 schema_version이 필요합니다.": (
        "Mediation analysis requires a schema_version parameter."
    ),
    "매개분석 변수가 변경되었습니다.": (
        "The mediation-analysis variables were updated."
    ),
    "조절된 매개분석 model은 7 또는 14여야 합니다.": (
        "The moderated-mediation model must be 7 or 14."
    ),
    "조절된 매개분석에는 X, 매개변수, 조절변수, 결과 변수가 모두 필요합니다.": (
        "Moderated mediation requires X, a mediator, a moderator, and an outcome variable."
    ),
    "조절된 매개분석 변수에는 중복이 있을 수 없습니다.": (
        "Moderated-mediation variables cannot contain duplicates."
    ),
    "조절된 매개분석 파라미터 schema_version이 필요합니다.": (
        "Moderated mediation requires a schema_version parameter."
    ),
    "조절된 매개분석 변수가 변경되었습니다.": (
        "The moderated-mediation variables were updated."
    ),
    "결과 변수는 수치형 척도이고 두 요인은 안전한 명목형 또는 서열형이어야 합니다.": (
        "The outcome must be a numeric scale variable, and both factors must be safely nominal or ordinal."
    ),
    "결과 변수는 척도형이고 두 요인은 명목형 또는 서열형이어야 합니다.": (
        "The outcome must be a scale variable, and both factors must be nominal or ordinal."
    ),
    "결과 변수에 지원하지 않는 값이 있어 사건값을 확인할 수 없습니다.": (
        "The outcome contains unsupported values, so the event value cannot be confirmed."
    ),
    "결과 변수에는 결측이 아닌 값이 정확히 두 개 있어야 합니다.": (
        "The outcome must contain exactly two nonmissing values."
    ),
    "결과 변수와 두 요인은 모두 선택되어야 하며 서로 달라야 합니다.": (
        "Select an outcome and two factors, and use a different variable for each role."
    ),
    "결과 변수와 예측 변수는 서로 다르고 중복이 없어야 합니다.": (
        "The outcome and predictors must differ, and predictors must not be duplicated."
    ),
    "모든 범주형 예측변수의 기준범주를 하나씩 선택해야 합니다.": (
        "Select one reference category for every categorical predictor."
    ),
    "범주형 기준범주 선택값은 변수별 매핑이어야 합니다.": (
        "Categorical reference selections must be a mapping keyed by variable."
    ),
    "범주형 예측변수의 수준을 안전하게 확인할 수 없습니다.": (
        "The categorical-predictor levels cannot be verified safely."
    ),
    "분석 설정을 확정했습니다. 실행은 아직 시작하지 않았습니다.": (
        "The analysis configuration was confirmed. Execution has not started."
    ),
    "선택한 사건값이 현재 데이터의 두 결과값과 일치하지 않습니다.": (
        "The selected event does not match either of the current outcome values."
    ),
    "설명 근거를 불러올 수 없습니다.": "The supporting explanation is unavailable.",
    "완전사례에서 각 요인은 구별 가능한 2~6개 수준을 가져야 합니다.": (
        "Each factor must have 2 to 6 distinct levels among complete cases."
    ),
    "완전사례의 요인 수준을 안전하게 확인할 수 없습니다.": (
        "The factor levels among complete cases cannot be verified safely."
    ),
    "이원 Type III 분산분석 설정이 변경되었습니다.": (
        "The two-factor Type III ANOVA configuration was updated."
    ),
    "이원 Type III 분산분석 설정이 올바르지 않습니다.": (
        "The two-factor Type III ANOVA configuration is invalid."
    ),
    "이항 로지스틱 회귀 설정이 변경되었습니다.": (
        "The binary logistic-regression configuration was updated."
    ),
    "이항 로지스틱 회귀 설정이 올바르지 않습니다.": (
        "The binary logistic-regression configuration is invalid."
    ),
    "이항 로지스틱 회귀에는 결과 변수와 예측 변수가 모두 필요합니다.": (
        "Binary logistic regression requires an outcome and predictors."
    ),
    "저장된 요인 수준이 현재 데이터의 수준과 일치하지 않습니다.": (
        "The stored factor levels do not match the current data."
    ),
    "현재 데이터에서 두 요인의 수준을 확인할 수 없습니다.": (
        "The levels of both factors cannot be verified in the current data."
    ),
    "현재 데이터에서 사건값을 확인할 수 없습니다.": (
        "The event value cannot be verified in the current data."
    ),
    "현재 데이터에서 이원 분산분석 변수를 확인할 수 없습니다.": (
        "The two-factor ANOVA variables cannot be verified in the current data."
    ),
    "현재 데이터에서 이항 결과값을 확인할 수 없습니다.": (
        "The binary outcome values cannot be verified in the current data."
    ),
    "현재 데이터의 변수 역할을 안전하게 확인할 수 없습니다.": (
        "The variable roles in the current data cannot be verified safely."
    ),
    "현재 데이터의 변수 척도를 확인할 수 없습니다.": (
        "The variable measures in the current data cannot be verified."
    ),
    "현재 데이터의 요인 수준을 안전하게 확인할 수 없습니다.": (
        "The factor levels in the current data cannot be verified safely."
    ),
    "현재 데이터의 이항 결과값을 안전하게 확인할 수 없습니다.": (
        "The binary outcome values in the current data cannot be verified safely."
    ),
    "그림": "Figure",
    "그림 파일을 찾을 수 없습니다": "Figure file could not be found",
}


def localize_message(message: object, language: str) -> str:
    text = "" if message is None else str(message)
    if language != "en" or not text:
        return text
    exact = UI_MESSAGE_EN.get(text)
    if exact is not None:
        return exact
    patterns = (
        (r"^알 수 없는 변수입니다: (.+)$", r"Unknown variable: \1"),
        (
            r"^패치 종류가 일치하지 않습니다: (.+)$",
            r"The patch type does not match: \1",
        ),
        (
            r"^(.+) 패치에 알 수 없는 필드가 있습니다: (.+)$",
            r"The \1 patch contains unknown fields: \2",
        ),
        (r"^필수 필드가 없습니다: (.+)$", r"A required field is missing: \1"),
        (r"^(.+) 필드는 문자열이어야 합니다\.$", r"The \1 field must be a string."),
        (r"^(.+) 필드는 목록이어야 합니다\.$", r"The \1 field must be a list."),
        (
            r"^(.+) 필드는 비어 있지 않은 목록이어야 합니다\.$",
            r"The \1 field must be a non-empty list.",
        ),
    )
    for pattern, replacement in patterns:
        translated, count = re.subn(pattern, replacement, text)
        if count:
            return translated
    return text
