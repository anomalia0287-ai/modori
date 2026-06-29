import QtQuick
import QtQuick.Controls

TableView {
    id: root
    clip: true
    reuseItems: true
    model: uiController.dataModel
    property string editPolicyText: "셀 직접 수정은 재현 가능한 편집 단계가 준비된 뒤 활성화됩니다."
    ToolTip.text: editPolicyText

    delegate: Rectangle {
        implicitWidth: 120
        implicitHeight: 32
        color: "#FFFFFF"
        border.color: "#E4ECE8"

        Text {
            anchors.centerIn: parent
            text: model.display ?? ""
            color: "#17211D"
            elide: Text.ElideRight
        }
    }
}
