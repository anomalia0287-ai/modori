import QtQuick

QtObject {
    readonly property color entryBrand: "#173B7A"
    readonly property color entryCanvas: "#F7F3EA"
    readonly property color entryCard: "#FFFDF8"
    readonly property color entryPrimary: "#2F5DA8"
    readonly property color entryText: "#17233A"
    readonly property color entryCardSelected: Qt.rgba(
        entryPrimary.r,
        entryPrimary.g,
        entryPrimary.b,
        0.10
    )
    readonly property color entryCardHover: Qt.rgba(
        entryPrimary.r,
        entryPrimary.g,
        entryPrimary.b,
        0.06
    )
    readonly property color entryDivider: Qt.rgba(
        entryText.r,
        entryText.g,
        entryText.b,
        0.14
    )
    readonly property color entryTextMuted: Qt.rgba(
        entryText.r,
        entryText.g,
        entryText.b,
        0.66
    )
    readonly property color entryOnBrand: entryCard
    readonly property color entryOnBrandMuted: Qt.rgba(
        entryCard.r,
        entryCard.g,
        entryCard.b,
        0.76
    )
    readonly property color workspaceBrand: entryBrand
    readonly property color workspaceCanvas: entryCanvas
    readonly property color workspaceCard: entryCard
    readonly property color workspacePrimary: entryPrimary
    readonly property color workspaceText: entryText
    readonly property color workspaceSelected: Qt.rgba(
        workspacePrimary.r,
        workspacePrimary.g,
        workspacePrimary.b,
        0.10
    )
    readonly property color workspaceHover: Qt.rgba(
        workspacePrimary.r,
        workspacePrimary.g,
        workspacePrimary.b,
        0.06
    )
    readonly property color workspaceDivider: Qt.rgba(
        workspaceText.r,
        workspaceText.g,
        workspaceText.b,
        0.14
    )
    readonly property color workspaceDividerStrong: Qt.rgba(
        workspaceText.r,
        workspaceText.g,
        workspaceText.b,
        0.28
    )
    readonly property color workspaceTextMuted: Qt.rgba(
        workspaceText.r,
        workspaceText.g,
        workspaceText.b,
        0.66
    )
    readonly property color workspacePrimaryHover: Qt.lighter(workspacePrimary, 1.08)
    readonly property color workspacePrimaryPressed: Qt.darker(workspacePrimary, 1.18)
    readonly property color workspaceFocus: workspacePrimary
    readonly property color workspaceOnPrimary: workspaceCard
    readonly property color canvasCream: workspaceCanvas
    readonly property color surfaceCream: workspaceCard
    readonly property color surfaceRaised: workspaceCanvas
    readonly property color surfaceQuiet: workspaceCanvas
    readonly property color pearlIce: workspaceCard
    readonly property color pearlRose: workspaceCard
    readonly property color pearlLilac: workspaceSelected
    readonly property color brandWordmark: workspaceBrand
    readonly property color auroraGlassTop: "#AACFD3"
    readonly property color auroraGlassMiddle: "#D5E1E1"
    readonly property color auroraGlassBottom: "#E8D7DC"
    readonly property color auroraNeutralTop: "#BCC9CA"
    readonly property color auroraNeutralMiddle: "#D5DCDC"
    readonly property color auroraNeutralBottom: "#E1DDDC"
    readonly property color auroraTiffanyBloom: "#69CEC6"
    readonly property color auroraIceBloom: "#B8DDE8"
    readonly property color auroraLilacBloom: "#CFC4E2"
    readonly property color auroraRoseBloom: "#E1BEC5"
    readonly property color auroraGlassVeil: "#FFFFFF"
    readonly property color auroraGlassAnchor: "#B9856E"
    readonly property color auroraTiffanyTransparent: Qt.rgba(auroraTiffanyBloom.r, auroraTiffanyBloom.g, auroraTiffanyBloom.b, 0)
    readonly property color auroraIceTransparent: Qt.rgba(auroraIceBloom.r, auroraIceBloom.g, auroraIceBloom.b, 0)
    readonly property color auroraLilacTransparent: Qt.rgba(auroraLilacBloom.r, auroraLilacBloom.g, auroraLilacBloom.b, 0)
    readonly property color auroraRoseTransparent: Qt.rgba(auroraRoseBloom.r, auroraRoseBloom.g, auroraRoseBloom.b, 0)
    readonly property color auroraVeilTransparent: Qt.rgba(auroraGlassVeil.r, auroraGlassVeil.g, auroraGlassVeil.b, 0)
    readonly property color footerGlassTop: "#C4D2D2"
    readonly property color footerGlassMiddle: "#D6D4D2"
    readonly property color footerGlassBottom: "#D8C5C5"
    readonly property color glassListSurface: workspaceCard
    readonly property color glassListHoverSurface: workspaceHover
    readonly property color glassListSheen: workspaceCard
    readonly property color modeChoiceSurface: workspaceCard
    readonly property color gridCellHoverSurface: workspaceHover
    readonly property color scrollRailSurface: workspaceDivider
    readonly property color scrollThumbSurface: workspaceTextMuted
    readonly property color scrollThumbActiveSurface: workspacePrimary
    readonly property color bronzeDeep: workspaceBrand
    readonly property color bronzeHover: workspacePrimaryHover
    readonly property color bronzeAction: workspacePrimary
    readonly property color bronzeFocus: workspaceFocus
    readonly property color bronzeWash: workspaceSelected
    readonly property color focusRing: workspaceFocus
    readonly property color semanticGlow: workspacePrimary
    readonly property color transparent: "transparent"

    readonly property color gold: "#B98B3E"
    readonly property color orange: "#B87743"
    readonly property color transformAccent: "#A96F78"
    readonly property color porcelainBackground: workspaceCanvas
    readonly property color guideSurface: workspaceCard
    readonly property color subtleSurface: workspaceCanvas
    readonly property color quietSurface: workspaceCanvas
    readonly property color popoverSurface: workspaceCard
    readonly property color paperSurface: workspaceCard
    readonly property color surface: workspaceCard
    readonly property color gridColumnHeaderSurface: workspaceCanvas
    readonly property color gridRowHeaderSurface: workspaceCanvas
    readonly property color gridHeaderText: workspaceText
    readonly property color flatBackground: workspaceCanvas
    readonly property color lineSubtle: workspaceDivider
    readonly property color lineStrong: workspaceDividerStrong
    readonly property color lineGrid: workspaceDivider
    readonly property color lineRail: workspaceDivider
    readonly property color lineDialog: workspaceDivider
    readonly property color linePopover: workspacePrimary
    readonly property color textStrong: workspaceText
    readonly property color textBody: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.82)
    readonly property color textControl: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.90)
    readonly property color textTable: workspaceText
    readonly property color textSecondary: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.72)
    readonly property color textLevel: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.76)
    readonly property color textMuted: workspaceTextMuted
    readonly property color textSoft: Qt.rgba(workspaceText.r, workspaceText.g, workspaceText.b, 0.52)
    readonly property color onBrand: workspaceOnPrimary
    readonly property color onBrandDanger: "#FFE6E6"
    readonly property color selectionSurface: workspaceSelected
    readonly property color warning: "#865F1B"
    readonly property color warningSurface: "#F5E8C8"
    readonly property color danger: "#A33D4B"
    readonly property color dangerSurface: "#F5E2E3"
    readonly property color brandScrim: "#80604438"

    readonly property string brandFontFamily: "Segoe UI"

    readonly property int radiusSmall: 6
    readonly property int radiusMedium: 10
    readonly property int radiusLarge: 14
    readonly property int checkboxRadius: 4
    readonly property int borderWidth: 1
    readonly property int borderWidthFocus: 2

    readonly property int spaceXs: 4
    readonly property int spaceTight: 6
    readonly property int spaceSm: 8
    readonly property int spaceGridColumn: 10
    readonly property int spaceMd: 12
    readonly property int spaceHeaderGap: 6
    readonly property int spaceContent: 16
    readonly property int spaceLg: 18
    readonly property int spaceRailHorizontal: 20
    readonly property int spaceXl: 24
    readonly property int spaceNone: 0
    readonly property int spaceGridRow: 8

    readonly property int fontHero: 44
    readonly property int fontSplashTitle: 30
    readonly property int fontSplashSubtitle: 13
    readonly property int fontSubtitle: 20
    readonly property int fontOverlay: 22
    readonly property int fontTitle: 16
    readonly property int fontSection: 14
    readonly property int fontBody: 12
    readonly property int fontCaption: 11
    readonly property int fontCommand: 11

    readonly property int windowDefaultWidth: 1180
    readonly property int windowDefaultHeight: 760
    readonly property int entryViewportMargin: 56
    readonly property int entryStartMaxWidth: 1000
    readonly property int entryStartMaxHeight: 580
    readonly property int entryBrandColumnWidth: 390
    readonly property int entryRecentMaxHeight: 132
    readonly property int entryCardPadding: 40
    readonly property int entryBrandRegionWidth: 430
    readonly property int entryBrandPanelPadding: 32
    readonly property int entryColumnGap: 36
    readonly property int entryContentMaxWidth: 650
    readonly property int entryContentTopMargin: 112
    readonly property int entryModeCardHeight: 82
    readonly property int entryPrimaryActionHeight: 52
    readonly property int entryRecentRowHeight: 54
    readonly property int entryRightHorizontalPadding: 64
    readonly property int entryTopActionMargin: 28
    readonly property int workOuterMargin: 12
    readonly property int detachedSheetWidth: 980
    readonly property int detachedSheetHeight: 640
    readonly property int headerHeight: 56
    readonly property int commandSurfaceHeight: 50
    readonly property int headerControlHeight: 30
    readonly property int headerControlHorizontalPadding: 12
    readonly property int headerHorizontalPadding: 16
    readonly property int workWordmarkSize: 18
    readonly property int workWordmarkCommandGap: 40
    readonly property int modeChoiceMinimumWidth: 104
    readonly property int tabHeight: 32
    readonly property int pipelineHeight: 176
    readonly property int pipelineCompactHeight: 68
    readonly property int resultsPanelPreferredWidth: 420
    readonly property int guideRailPreferredWidth: 260
    readonly property int guideRailEnglishPreferredWidth: 300
    readonly property int guideRailMinimumWidth: 220
    readonly property int guideRailMaximumWidth: 360
    readonly property int dialogViewportMargin: 48
    readonly property int importDialogMaxWidth: 760
    readonly property int importDialogMaxHeight: 620
    readonly property int importPreviewColumnWidth: 410
    readonly property int importPreviewColumnMinimumWidth: 320
    readonly property int importSettingsColumnMinimumWidth: 250
    readonly property int importReviewMaxHeight: 132
    readonly property int importColumnMinimumHeight: 96
    readonly property int importSettingsHeight: 264
    readonly property int importReviewRowNumberWidth: 24
    readonly property int importReviewRowSpacing: 1
    readonly property int popoverWidth: 420
    readonly property int popoverBodyHeight: 320
    readonly property int progressWidth: 280
    readonly property int splashProgressWidth: 180
    readonly property int splashProgressHeight: 4
    readonly property int splashProgressSegmentWidth: 54
    readonly property int splashProgressCycleMs: 1050
    readonly property int tableCellWidth: 120
    readonly property int tableCellHeight: 32
    readonly property int gridAutoFitSampleRows: 40
    readonly property int gridColumnAutoMinWidth: 96
    readonly property int gridColumnAutoMaxWidth: 360
    readonly property int gridColumnManualMinWidth: 72
    readonly property int gridColumnManualMaxWidth: 640
    readonly property int gridColumnMeasurePadding: 24
    readonly property int gridHeaderHeight: 28
    readonly property int gridRowLabelWidth: 56
    readonly property int gridStatusHeight: 28
    readonly property int gridScrollRailSize: 12
    readonly property int gridScrollTrackThickness: 3
    readonly property int gridScrollThumbThickness: 5
    readonly property int gridScrollThumbActiveThickness: 7
    readonly property int gridScrollMinimumThumbLength: 28
    readonly property int gridScrollSettleDurationMs: 110
    readonly property int gridScrollThicknessDurationMs: 90
    readonly property int variableCellWidth: 140
    readonly property int variableCellHeight: 34
    readonly property int fieldWidthTiny: 80
    readonly property int fieldWidthSmall: 130
    readonly property int fieldWidthMedium: 180
    readonly property int badgeHeight: 22
    readonly property int badgeHorizontalPadding: 18
    readonly property int controlHeight: 34
    readonly property int iconButtonSize: 32
    readonly property int iconSize: 16
    readonly property int compactGlyphSize: 12
    readonly property int checkboxIndicatorSize: 18
    readonly property int radioDotSize: 8
    readonly property int spinIndicatorWidth: 28
    readonly property int switchTrackWidth: 38
    readonly property int switchTrackHeight: 20
    readonly property int switchThumbSize: 16
    readonly property int switchThumbInset: 2
    readonly property int preferenceMinimumWidth: 320
    readonly property int settingsDialogWidth: 520
    readonly property int resultDetailWidth: 820
    readonly property int resultDetailHeight: 560
    readonly property int reportDialogWidth: 560
    readonly property int reportDialogHeight: 520
    readonly property int tooltipDelayMs: 450
    readonly property int tablePreviewHeight: 206
    readonly property int chartPreviewHeight: 228
    readonly property int radiusPill: 999
    readonly property int splashFastDelayMs: 100
    readonly property int splashDelayMs: 800
    readonly property int screenTransitionDuration: 160
    readonly property int overlayLayer: 100

    readonly property real opacityFull: 1.0
    readonly property real opacityNone: 0.0
    readonly property real opacityHigh: 0.9
    readonly property real brandLetterSpacing: 2.4
    readonly property real auroraTiffanyOpacity: 0.48
    readonly property real auroraChromaticOpacity: 0.54
    readonly property real footerAuroraChromaticOpacity: 0.38
    readonly property real auroraVeilOpacity: 0.18
    readonly property real auroraSheenOpacity: 0.62
    readonly property real auroraAnchorOpacity: 0.58
    readonly property real opacityPrivacy: 0.86
    readonly property real opacitySplashPrivacy: 0.85
    readonly property real opacitySoft: 0.72
    readonly property real opacityScrollThumbRest: 0.72
    readonly property real opacityDisabled: 0.46
    readonly property real stateBorderAlpha: 0.25
    readonly property real resultSummaryLineHeight: 1.18
    readonly property real entryPromiseLineHeight: 1.35
    readonly property real entryBrandRatio: 0.37
}
