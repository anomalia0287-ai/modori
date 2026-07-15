import QtQuick
import "../theme"

Text {
    id: root

    color: theme.brandWordmark
    font.family: parisienne.name
    font.pixelSize: theme.fontSubtitle
    font.weight: Font.Normal
    Accessible.name: text

    FontLoader {
        id: parisienne
        source: Qt.resolvedUrl("../assets/fonts/Parisienne-Regular.ttf")
    }

    Theme {
        id: theme
    }
}
