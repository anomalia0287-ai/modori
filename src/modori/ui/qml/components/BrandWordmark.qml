import QtQuick
import "../theme"

Text {
    id: root

    color: theme.brandWordmark
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
