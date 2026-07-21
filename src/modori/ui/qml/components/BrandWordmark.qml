import QtQuick
import "../theme"

Text {
    id: root

    property color foregroundColor: theme.brandWordmark

    color: root.foregroundColor
    font.family: theme.brandFontFamily
    font.pixelSize: theme.fontSubtitle
    font.weight: Font.DemiBold
    font.capitalization: Font.AllUppercase
    font.letterSpacing: theme.brandLetterSpacing
    Accessible.name: text

    Theme {
        id: theme
    }
}
