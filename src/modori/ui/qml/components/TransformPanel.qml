import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property bool canEditTransform: uiController.status !== "empty" && uiController.status !== "running"

    function hasText(value) {
        return String(value).trim().length > 0
    }

    function methodValue(label) {
        if (label === appBootstrap.text("transform.method_sum")) {
            return "sum"
        }
        return "mean"
    }

    function policyValue(label) {
        if (label === appBootstrap.text("transform.policy_conservative")) {
            return "conservative"
        }
        if (label === appBootstrap.text("transform.policy_custom")) {
            return "custom"
        }
        return "survey"
    }

    ScrollView {
        id: transformScroll
        anchors.fill: parent
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: transformScroll.availableWidth
            spacing: 12

            Label {
                text: appBootstrap.text("transform.source_protected")
                color: "#486157"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.topMargin: 12
            }

            GroupBox {
                title: appBootstrap.text("transform.reverse_title")
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: 8
                    columnSpacing: 10

                    Label {
                        text: appBootstrap.text("transform.reverse_columns")
                        color: "#26352F"
                    }

                    TextField {
                        id: reverseColumns
                        placeholderText: appBootstrap.text("transform.reverse_columns_placeholder")
                        Accessible.name: appBootstrap.text("transform.reverse_columns")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_min")
                        color: "#26352F"
                    }

                    SpinBox {
                        id: reverseMin
                        from: -999
                        to: 999
                        value: 1
                        Accessible.name: appBootstrap.text("transform.scale_min")
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_max")
                        color: "#26352F"
                    }

                    SpinBox {
                        id: reverseMax
                        from: -999
                        to: 999
                        value: 5
                        Accessible.name: appBootstrap.text("transform.scale_max")
                    }

                    Label {
                        text: appBootstrap.text("transform.reverse_suffix")
                        color: "#26352F"
                    }

                    TextField {
                        id: reverseSuffix
                        text: appBootstrap.text("transform.reverse_suffix_placeholder")
                        placeholderText: appBootstrap.text("transform.reverse_suffix_placeholder")
                        Accessible.name: appBootstrap.text("transform.reverse_suffix")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Item {}

                    Button {
                        text: appBootstrap.text("transform.apply_reverse")
                        Accessible.name: appBootstrap.text("transform.apply_reverse")
                        enabled: root.canEditTransform && root.hasText(reverseColumns.text)
                        onClicked: uiController.reverseCodeFromText(
                            reverseColumns.text,
                            reverseSuffix.text,
                            reverseMin.value,
                            reverseMax.value
                        )
                    }
                }
            }

            GroupBox {
                title: appBootstrap.text("transform.scale_title")
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.bottomMargin: 12

                GridLayout {
                    columns: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    rowSpacing: 8
                    columnSpacing: 10

                    Label {
                        text: appBootstrap.text("transform.scale_items")
                        color: "#26352F"
                    }

                    TextField {
                        id: scaleItems
                        placeholderText: appBootstrap.text("transform.scale_items_placeholder")
                        Accessible.name: appBootstrap.text("transform.scale_items")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_name")
                        color: "#26352F"
                    }

                    TextField {
                        id: scaleName
                        placeholderText: appBootstrap.text("transform.scale_name_placeholder")
                        Accessible.name: appBootstrap.text("transform.scale_name")
                        Layout.fillWidth: true
                        selectByMouse: true
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_method")
                        color: "#26352F"
                    }

                    ComboBox {
                        id: scaleMethod
                        model: [
                            appBootstrap.text("transform.method_mean"),
                            appBootstrap.text("transform.method_sum")
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_method")
                    }

                    Label {
                        text: appBootstrap.text("transform.scale_policy")
                        color: "#26352F"
                    }

                    ComboBox {
                        id: scalePolicy
                        model: [
                            appBootstrap.text("transform.policy_survey"),
                            appBootstrap.text("transform.policy_conservative"),
                            appBootstrap.text("transform.policy_custom")
                        ]
                        Accessible.name: appBootstrap.text("transform.scale_policy")
                    }

                    Label {
                        text: appBootstrap.text("transform.min_valid")
                        color: "#26352F"
                    }

                    SpinBox {
                        id: minValid
                        from: 1
                        to: 100
                        value: 80
                        Accessible.name: appBootstrap.text("transform.min_valid")
                    }

                    Item {}

                    Button {
                        text: appBootstrap.text("transform.apply_scale")
                        Accessible.name: appBootstrap.text("transform.apply_scale")
                        enabled: root.canEditTransform && root.hasText(scaleItems.text) && root.hasText(scaleName.text)
                        onClicked: uiController.scaleScoreFromText(
                            scaleItems.text,
                            scaleName.text,
                            root.methodValue(scaleMethod.currentText),
                            root.policyValue(scalePolicy.currentText),
                            minValid.value / 100
                        )
                    }
                }
            }
        }
    }
}
