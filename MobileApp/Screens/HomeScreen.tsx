import { useEffect, useRef, useState } from "react";
import { Button, FlatList, Image, Pressable, StyleSheet, Text, View, Modal, TouchableOpacity, TouchableWithoutFeedback, TextInput, ScrollView, Alert, ActivityIndicator, Dimensions } from "react-native";
import { AntDesign, MaterialIcons, Ionicons, FontAwesome } from "@expo/vector-icons";

const screenHeight = Dimensions.get('window').height;
const screenWidth = Dimensions.get('window').width;

interface BloodPressureData {
    systolic: number;
    diastolic: number;
    pulse: number;
    time: string;
}

export default function HomeScreen({ navigation, setIsCameraActive, route }: { navigation: any; setIsCameraActive: (active: boolean) => void, route: any }) {
    const [readings, setReadings] = useState<BloodPressureData[]>([]);
    const defaultReading = {
        diastolic: 0,
        pulse: 0,
        systolic: 0,
        time: ""
    };
    const [userData, setUserData] = useState({
        username: '',
        citizenId: '',
        dateOfBirth: '',
        bloodType: '',
        height: '',
        weight: '',
        age: '',
        gender: '',
        email: '',
        role: '',
    });

    useEffect(() => {
        setReadings([defaultReading]);
    }, []);

    useEffect(() => {
        if (route.params?.userData) {
            setUserData(route.params.userData);
            console.log("HomeScreen, userData:", route.params.userData);
        }
    }, [route.params?.userData]);

    useEffect(() => {
        if (!route.params?.bloodPressureData) {
            if (readings.length === 0) {
                setReadings([defaultReading]);
            }
        } else {
            if (route.params?.allReadings) {
                setReadings(route.params.allReadings);
            } else {
                setReadings(prevReadings => {
                    const newReading = route.params.bloodPressureData;
                    if (newReading.systolic === 0 && newReading.diastolic === 0) {
                        return prevReadings;
                    }
                    return [...prevReadings, newReading];
                });
            }
        }
        console.log(readings);
    }, [route.params?.bloodPressureData, route.params?.allReadings]);

    useEffect(() => {
        console.log('readings has been updated:', readings);
    }, [readings]);

    // Profile section
    const ProfileSection = () => (
        <View style={styles.profileSection}>
            <View style={styles.avatarCircle}>
                <Ionicons name="person" size={36} color="#4662e6" />
            </View>
            <View style={{ marginLeft: 8 }}>
                <Text style={styles.helloText}>Hello!</Text>
                <Text style={styles.usernameText}>{userData.username}</Text>
            </View>
        </View>
    );

    // Discard section
    const DiscardSection = () => (
        <TouchableOpacity style={styles.discardSection} onPress={() => Alert.alert('Discard', 'Discard pressed!')}>
            <Text style={styles.discardText}>Discard</Text>
            <MaterialIcons name="delete-outline" size={22} color="#e74c3c" style={{ marginLeft: 2 }} />
        </TouchableOpacity>
    );

    // Reading card
    const renderReading = ({ item, isLatest }: { item: BloodPressureData, isLatest: boolean }) => (
        <View style={[isLatest ? styles.latestReadingCard : styles.readingCard, styles.shadow, { marginBottom: 20 }]}> 
            <View style={styles.readingHeaderRow}>
                <Text style={isLatest ? styles.latestTimeText : styles.timeText}>
                    {item.time || defaultReading.time}
                </Text>
            </View>
            <View style={styles.readingValuesRow}>
                <View style={styles.valueContainer}>
                    <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Systolic</Text>
                    <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.systolic || defaultReading.systolic}</Text>
                </View>
                <View style={styles.valueContainer}>
                    <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Diastolic</Text>
                    <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.diastolic || defaultReading.diastolic}</Text>
                </View>
                <View style={styles.valueContainer}>
                    <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Pulse</Text>
                    <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.pulse || defaultReading.pulse}</Text>
                </View>
            </View>
        </View>
    );

    // Bottom navigation bar
    const BottomBar = () => (
        <View style={styles.bottomBar}>
            <TouchableOpacity style={styles.bottomBarIconActive}>
                <Ionicons name="home" size={28} color="#1ccfc0" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Camera", { existingReadings: readings })}>
                <Ionicons name="scan" size={28} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon}>
                <FontAwesome name="medkit" size={28} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Account", {userData: userData})}>
                <Ionicons name="person-circle-outline" size={28} color="#fff" />
            </TouchableOpacity>
        </View>
    );

    // Main render
    return (
        <View style={styles.container}>
            <View style={styles.topRow}>
                <ProfileSection />
                <DiscardSection />
            </View>
            <ScrollView contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
                {/* Blood Pressure Readings */}
                <View style={styles.readingsContainer}>
                    {[...readings].reverse().map((reading, idx, arr) => (
                        <View key={reading.time + idx} style={styles.readingWrapper}>
                            {renderReading({ item: reading, isLatest: idx === 0 })}
                        </View>
                    ))}
                </View>
            </ScrollView>
            <BottomBar />
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: "#fff",
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 32,
        marginHorizontal: 24,
        marginBottom: 12,
    },
    profileSection: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    avatarCircle: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: '#f2f2f2',
        justifyContent: 'center',
        alignItems: 'center',
    },
    helloText: {
        fontSize: 14,
        color: '#333',
    },
    usernameText: {
        fontSize: 16,
        color: '#4662e6',
        fontWeight: 'bold',
    },
    discardSection: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    discardText: {
        color: '#e74c3c',
        fontSize: 16,
        fontWeight: '500',
        marginRight: 2,
    },
    scrollContainer: {
        paddingBottom: 100,
        paddingHorizontal: 0,
    },
    readingsContainer: {
        paddingHorizontal: 0,
        alignItems: 'center',
    },
    readingWrapper: {
        width: screenWidth * 0.92,
    },
    latestReadingCard: {
        backgroundColor: '#4662e6',
        borderRadius: 20,
        padding: 20,
        marginTop: 10,
        marginBottom: 0,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 6,
    },
    readingCard: {
        backgroundColor: '#fff',
        borderRadius: 20,
        borderWidth: 1,
        borderColor: '#222',
        padding: 20,
        marginTop: 10,
        marginBottom: 0,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 4,
        elevation: 2,
    },
    shadow: {},
    readingHeaderRow: {
        marginBottom: 10,
    },
    timeText: {
        fontSize: 16,
        color: '#222',
        fontWeight: '400',
    },
    latestTimeText: {
        fontSize: 16,
        color: '#fff',
        fontWeight: '400',
    },
    readingValuesRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 8,
    },
    valueContainer: {
        alignItems: 'center',
        flex: 1,
    },
    valueLabel: {
        fontSize: 16,
        color: '#222',
        fontWeight: '600',
        marginBottom: 4,
    },
    latestValueLabel: {
        fontSize: 16,
        color: '#fff',
        fontWeight: '600',
        marginBottom: 4,
    },
    valueNumber: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#222',
    },
    latestValueNumber: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#fff',
    },
    bottomBar: {
        position: "absolute",
        bottom: 16,
        left: 10,
        right: 10,
        height: 64,
        backgroundColor: "#222",
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'center',
        borderRadius: 32,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 8,
    },
    bottomBarIcon: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    bottomBarIconActive: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'transparent',
    },
});