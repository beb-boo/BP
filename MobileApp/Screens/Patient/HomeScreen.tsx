import { useEffect, useRef, useState } from "react";
import { Button, FlatList, Image, Pressable, StyleSheet, Text, View, Modal, TouchableOpacity, TouchableWithoutFeedback, TextInput, ScrollView, Alert, ActivityIndicator, Dimensions } from "react-native";
import { AntDesign, MaterialIcons, Ionicons, FontAwesome } from "@expo/vector-icons";
import { bloodPressureApi } from '../../api/bloodPressure';
import { authApi } from "../../api/auth";

const screenHeight = Dimensions.get('window').height;
const screenWidth = Dimensions.get('window').width;

interface BloodPressureData {
    id?: number;
    created_at?: string;
    systolic: number;
    diastolic: number;
    pulse: number;
    time: string;
}

export default function HomeScreen({ navigation, route }: { navigation: any, route: any }) {
    const [readings, setReadings] = useState<BloodPressureData[]>([]);
    const [userData, setUserData] = useState({
        id: null,
        email: '',
        phone_number: '',
        full_name: '',
        role: '',
        citizen_id: '',
        medical_license: '',
        date_of_birth: '',
        gender: '',
        blood_type: '',
        height: '',
        weight: '',
        is_active: false,
        is_email_verified: false,
        is_phone_verified: false,
        last_login: '',
        created_at: '',
        updated_at: '',
    });

    useEffect(() => {
        const fetchBPRecords = async () => {
            try {
                const response = await bloodPressureApi.getRecords();
                const records = response.data?.records || [];
                console.log(records)
                setReadings(records.length > 0 ? records : []);
            } catch (error) {
                console.log('Error fetching BP records:', error);
                setReadings([]);
            }
        };

        fetchBPRecords();
    }, []);

    useEffect(() => {
        if (route.params?.bloodPressureData) {
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

    useEffect(() => {
        // Always fetch from backend on mount
        const fetchProfile = async () => {
            const response = await authApi.getCurrentUser();
            const profile = response.data.profile; // Extract the profile from nested structure
            setUserData(profile);
            console.log('Home1 ', profile);
            console.log(profile.full_name);
        };
        fetchProfile();
    }, []);

    useEffect(() => {
        // If route param changes and has userProfile, update state
        if (route.params?.userProfile) {
            const profile = route.params.userProfile.data.profile; // Extract the profile from nested structure
            setUserData(profile);
            console.log('Home2 ', profile);
            console.log(profile.full_name);
        }
    }, [route.params?.userProfile]);

    const discardRecord = async (id: number) => {
        await bloodPressureApi.deleteRecord(id);
        const response = await bloodPressureApi.getRecords();
        const records = response.data?.records || [];
        console.log(records)
        setReadings(records.length > 0 ? records : []);
    };

    // Profile section
    const ProfileSection = () => (
        <View style={styles.profileSection}>
            <View style={{ marginLeft: 8 }}>
                <Text style={styles.helloText}>Hello!</Text>
                <Text style={styles.usernameText}>{userData.full_name}</Text>
            </View>
        </View>
    );

    // Discard section
    const DiscardSection = ({ id }: { id: number }) => (
        <TouchableOpacity style={styles.discardSection} onPress={() => Alert.alert('Delete Confirmation', 'Do you want to delete this record ? This action cannot be undone.',
            [
                {
                    text: 'Confirm',
                    onPress: () => discardRecord(id),
                },
                {
                    text: 'cancel',
                    onPress: () => Alert.alert
                },

            ], { cancelable: true },)}>
            <MaterialIcons name="delete-outline" size={22} color="#e74c3c" style={{ marginLeft: 2 }} />
        </TouchableOpacity>
    );

    // Reading card
    const renderReading = ({ item, isLatest }: { item: BloodPressureData, isLatest: boolean }) => {
        let dateStr = '';
        let timeStr = '';
        if ((item as any).measurement_date) {
            const dateObj = new Date((item as any).measurement_date);
            dateStr = dateObj.toLocaleDateString('en-GB');
            // Use measurement_time if present, else fallback to time field
            timeStr = (item as any).measurement_time || item.time || dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (item.created_at) {
            const dateObj = new Date(item.created_at);
            dateStr = dateObj.toLocaleDateString('en-GB');
            timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return (
            <View style={[isLatest ? styles.latestReadingCard : styles.readingCard, styles.shadow, { marginBottom: 20 }]}>

                <View style={styles.readingHeaderRowFlex}>
                    <Text style={[isLatest ? styles.latestDateText : styles.dateText]}>{dateStr}</Text>
                    <Text style={[isLatest ? styles.latestTimeText : styles.timeText]}>{timeStr}</Text>
                </View>
                <View style={styles.readingValuesRow}>
                    <View style={styles.valueContainer}>
                        <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Systolic</Text>
                        <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.systolic}</Text>
                    </View>
                    <View style={styles.valueContainer}>
                        <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Diastolic</Text>
                        <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.diastolic}</Text>
                    </View>
                    <View style={styles.valueContainer}>
                        <Text style={isLatest ? styles.latestValueLabel : styles.valueLabel}>Pulse</Text>
                        <Text style={isLatest ? styles.latestValueNumber : styles.valueNumber}>{item.pulse}</Text>
                    </View>
                    {item.id !== undefined && <DiscardSection id={item.id} />}
                </View>

            </View>
        );
    };

    // Bottom navigation bar
    const BottomBar = () => (
        <View style={styles.bottomBar}>
            <TouchableOpacity style={styles.bottomBarIconActive}>
                <Ionicons name="home" size={28} color="#1ccfc0" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Camera")}>
                <Ionicons name="scan" size={28} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => userData.role === 'doctor' ? (navigation.navigate("Patientlist")) : (navigation.navigate("Doctorlist"))}>
                <FontAwesome name="medkit" size={28} color="#fff" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.bottomBarIcon} onPress={() => navigation.navigate("Account")}>
                <Ionicons name="person-circle-outline" size={28} color="#fff" />
            </TouchableOpacity>
        </View>
    );

    // Main render
    return (
        <View style={styles.container}>
            <View style={styles.topRow}>
                <ProfileSection />
            </View>
            <ScrollView contentContainerStyle={styles.scrollContainer} showsVerticalScrollIndicator={false}>
                {/* Blood Pressure Readings */}
                <View style={styles.readingsContainer}>
                    {readings.length > 0 ? (
                        readings
                            .slice()
                            .sort((a, b) => {
                                // Prefer measurement_date, fallback to created_at
                                const dateA = (a as any).measurement_date ? new Date((a as any).measurement_date) : (a.created_at ? new Date(a.created_at) : null);
                                const dateB = (b as any).measurement_date ? new Date((b as any).measurement_date) : (b.created_at ? new Date(b.created_at) : null);
                                if (dateA && dateB) {
                                    return dateB.getTime() - dateA.getTime(); // Descending
                                } else if (dateA) {
                                    return -1;
                                } else if (dateB) {
                                    return 1;
                                } else {
                                    return 0;
                                }
                            })
                            .map((reading, idx, arr) => {
                                const key = reading.id ?? reading.created_at ?? (reading.time + '-' + idx) ?? idx;
                                return (
                                    <View key={key} style={styles.readingWrapper}>
                                        {renderReading({ item: reading, isLatest: idx === 0 })}
                                    </View>
                                );
                            })
                    ) : (
                        <View style={styles.noRecordsContainer}>
                            <Ionicons name="heart-outline" size={64} color="#ccc" />
                            <Text style={styles.noRecordsTitle}>No Blood Pressure Records</Text>
                            <Text style={styles.noRecordsMessage}>
                                You haven't recorded any blood pressure readings yet.{'\n'}
                                Tap the scan button below to add your first reading.
                            </Text>
                        </View>
                    )}
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
        marginTop: 20,
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
        fontSize: 16,
        color: '#333',
    },
    usernameText: {
        fontSize: 24,
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
    noRecordsContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 40,
        marginTop: 60,
    },
    noRecordsTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
        marginTop: 16,
        marginBottom: 8,
    },
    noRecordsMessage: {
        fontSize: 16,
        color: '#666',
        textAlign: 'center',
        lineHeight: 24,
    },
    readingHeaderRowFlex: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10,
    },
    dateText: {
        fontSize: 16,
        color: '#222',
        fontWeight: '400',
    },
    latestDateText: {
        fontSize: 16,
        color: '#fff',
        fontWeight: '400',
    },
});